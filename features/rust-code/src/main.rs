use std::fs::File;
use std::io::{self, BufRead};
use std::path::Path;
use walkdir::WalkDir;
use regex::{Regex, RegexSet};
use serde::Serialize;
use serde_json::to_writer_pretty;
use indicatif::ProgressBar;
use rayon::prelude::*;
use std::sync::{Arc, Mutex};
use git2::{Repository, Time, BranchType};
use chrono::{NaiveDateTime, Utc, TimeZone};
use std::error::Error;
use std::io::BufReader;


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

fn load_regexes_from_file(file_path: &str) -> Result<Vec<(String, Regex)>, Box<dyn Error>> {
    let file = File::open(file_path)?;
    let reader = BufReader::new(file);
    let mut regexes = Vec::new();

    for line in reader.lines() {
        let line = line?.trim().to_string();

        if !line.is_empty() {
            // Remove os parênteses e as aspas da linha
            let line = line.trim_matches(|c| c == '(' || c == ')' || c == '"');
            let parts: Vec<&str> = line.split(',').map(|s| s.trim()).collect();

            if parts.len() == 2 {
                let feature = parts[0].to_string();
                let pattern = parts[1].trim_matches('r').trim_matches('"').to_string();
                let regex = Regex::new(&pattern)?;
                regexes.push((feature, regex));
            } else {
                eprintln!("Linha malformada no arquivo de regex: {}", line);
            }
        }
    }

    Ok(regexes)
}

fn search_features_in_file(file_path: &Path, regexes: &[(String, Regex)], regex_set: &RegexSet, results: &Arc<Mutex<Vec<FeatureOccurrence>>>) -> io::Result<()> {
    let file = File::open(file_path)?;
    for (index, line) in io::BufReader::new(file).lines().enumerate() {
        let line = line?;
        let matches: Vec<_> = regex_set.matches(&line).into_iter().collect();
        if !matches.is_empty() {
            let mut results_lock = results.lock().unwrap();
            for &match_idx in &matches {
                let (feature, _) = &regexes[match_idx];
                results_lock.push(FeatureOccurrence {
                    feature: feature.clone(),
                    path: file_path.to_string_lossy().to_string(),
                    line: index + 1,
                    commit_hash: None,
                    author: None,
                    date: None,
                    commit_message: None,
                    branch: None,
                });
                println!("Encontrado: {} em {}:{}", feature, file_path.to_string_lossy(), index + 1);
            }
        }
    }
    Ok(())
}

fn format_commit_time(time: Time) -> String {
    let seconds = time.seconds();
    let naive_time = NaiveDateTime::from_timestamp(seconds, 0); 
    let datetime = Utc.from_utc_datetime(&naive_time);
    datetime.format("%Y-%m-%d %H:%M:%S").to_string()
}

fn search_features_in_commits(repo: &Repository, regexes: &[(String, Regex)], regex_set: &RegexSet, results: &Arc<Mutex<Vec<FeatureOccurrence>>>) -> Result<(), git2::Error> {
    let mut revwalk = repo.revwalk()?;
    revwalk.push_head()?;
    for oid in revwalk {
        let oid = oid?;
        let commit = repo.find_commit(oid)?;
        let message = commit.message().unwrap_or("");
        let matches: Vec<_> = regex_set.matches(message).into_iter().collect();
        if !matches.is_empty() {
            let mut results_lock = results.lock().unwrap();
            for &match_idx in &matches {
                let (feature, _) = &regexes[match_idx];
                results_lock.push(FeatureOccurrence {
                    feature: feature.clone(),
                    path: "Commit Message".to_string(),
                    line: 0,
                    commit_hash: Some(commit.id().to_string()),
                    author: Some(commit.author().name().unwrap_or("Unknown").to_string()),
                    date: Some(format_commit_time(commit.time())),
                    commit_message: Some(message.to_string()),
                    branch: None,
                });
                println!("Encontrado em commit: {} - {}", commit.id(), feature);
            }
        }
    }
    Ok(())
}

fn search_features_in_branches(repo: &Repository, regexes: &[(String, Regex)], regex_set: &RegexSet, results: &Arc<Mutex<Vec<FeatureOccurrence>>>) -> Result<(), git2::Error> {
    let branches = repo.branches(Some(BranchType::Remote))?;
    for branch in branches {
        let (branch, _) = branch?;
        let branch_name = branch.name()?.unwrap_or("Unnamed").to_string();
        let commit = branch.get().peel_to_commit()?;
        let message = commit.message().unwrap_or("");
        let matches: Vec<_> = regex_set.matches(message).into_iter().collect();
        if !matches.is_empty() {
            let mut results_lock = results.lock().unwrap();
            for &match_idx in &matches {
                let (feature, _) = &regexes[match_idx];
                results_lock.push(FeatureOccurrence {
                    feature: feature.clone(),
                    path: "Branch".to_string(),
                    line: 0,
                    commit_hash: Some(commit.id().to_string()),
                    author: Some(commit.author().name().unwrap_or("Unknown").to_string()),
                    date: Some(format_commit_time(commit.time())),
                    commit_message: Some(message.to_string()),
                    branch: Some(branch_name.clone()),
                });
                println!("Encontrado na branch: {} - {}", branch_name, feature);
            }
        }
    }
    Ok(())
}

fn run_search_in_files(directory: &str, regexes: &[(String, Regex)], regex_set: &RegexSet, results: &Arc<Mutex<Vec<FeatureOccurrence>>>, target_extensions: &[&str]) {
    let files: Vec<_> = WalkDir::new(directory)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            e.path().is_file() &&
            e.path().extension().and_then(|s| s.to_str()).map_or(false, |ext| target_extensions.contains(&ext))
        })
        .collect();

    let pb = ProgressBar::new(files.len() as u64);

    files.par_iter().for_each(|entry| {
        let path = entry.path();
        if let Err(err) = search_features_in_file(path, regexes, regex_set, results) {
            eprintln!("Erro ao processar arquivo {}: {}", path.to_string_lossy(), err);
        }
        pb.inc(1);
    });

    pb.finish_with_message("Scan complete");
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let directory = r"src/linux";
    let regex_file_path = "src/regex.txt";
    let regexes = load_regexes_from_file(regex_file_path)?;

    let regex_set = RegexSet::new(
        regexes.iter().map(|(_, regex)| regex.as_str())
    ).unwrap();

    let results = Arc::new(Mutex::new(Vec::new()));

    run_search_in_files(directory, &regexes, &regex_set, &results, &["c", "h", "txt"]);

    let repo = Repository::discover(directory)?;
    search_features_in_commits(&repo, &regexes, &regex_set, &results)?;
    search_features_in_branches(&repo, &regexes, &regex_set, &results)?;

    let output_file = File::create("results.json")?;
    let results = Arc::try_unwrap(results).expect("Erro ao desbloquear Arc").into_inner().unwrap();
    to_writer_pretty(output_file, &results)?;

    println!("Resultado salvo em results.json");

    Ok(())
}
