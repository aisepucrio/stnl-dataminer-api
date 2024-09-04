use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use walkdir::WalkDir;
use regex::{Regex, RegexSet};
use serde::Serialize;
use serde_json::to_writer_pretty;
use indicatif::ProgressBar;
use rayon::prelude::*;
use std::sync::{Arc, Mutex};
use git2::{Repository};
use chrono::{Utc};

#[derive(Serialize, Debug)]
struct FeatureOccurrence {
    feature: String,
    path: String,
    line: usize,
    commit_hash: Option<String>,
    author: Option<String>,
    date: Option<String>,
    commit_message: Option<String>,
    branch: Option<String>,
}

// Função para carregar regexes de um arquivo
#[pyfunction]
fn load_regexes_from_file(file_path: &str) -> PyResult<Vec<(String, String)>> {
    let file = File::open(file_path).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let reader = BufReader::new(file);
    let mut regexes = Vec::new();

    for line in reader.lines() {
        let line = line.map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        let line = line.trim().to_string();
        if !line.is_empty() {
            let parts: Vec<&str> = line.split(',').map(|s| s.trim()).collect();
            if parts.len() == 2 {
                regexes.push((parts[0].to_string(), parts[1].to_string()));
            }
        }
    }
    Ok(regexes)
}

// Função para executar a busca em arquivos
#[pyfunction]
fn run_search_in_files(directory: &str, regex_file_path: &str) -> PyResult<()> {
    let regexes = load_regexes_from_file(regex_file_path)?;
    let regex_set = RegexSet::new(regexes.iter().map(|(_, regex)| regex)).unwrap();
    
    let results = Arc::new(Mutex::new(Vec::new()));
    let files: Vec<_> = WalkDir::new(directory)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_file())
        .collect();

    let pb = ProgressBar::new(files.len() as u64);

    files.par_iter().for_each(|entry| {
        let path = entry.path();
        if let Ok(content) = std::fs::read_to_string(path) {
            for (feature, regex) in &regexes {
                let re = Regex::new(regex).unwrap();
                for (i, line) in content.lines().enumerate() {
                    if re.is_match(line) {
                        let occurrence = FeatureOccurrence {
                            feature: feature.clone(),
                            path: path.to_string_lossy().to_string(),
                            line: i + 1,
                            commit_hash: None,
                            author: None,
                            date: None,
                            commit_message: None,
                            branch: None,
                        };
                        results.lock().unwrap().push(occurrence);
                    }
                }
            }
        }
        pb.inc(1);
    });

    pb.finish_with_message("Scan complete");
    let output_file = File::create("results.json").map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let results = Arc::try_unwrap(results).unwrap().into_inner().unwrap();
    to_writer_pretty(output_file, &results).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    println!("Resultado salvo em results.json");
    Ok(())
}

#[pymodule]
fn features_mining_rust(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(load_regexes_from_file, m)?)?;
    m.add_function(wrap_pyfunction!(run_search_in_files, m)?)?;
    Ok(())
}

fn main() {
    // O main pode ser deixado vazio se for apenas utilizado como módulo Python
}
