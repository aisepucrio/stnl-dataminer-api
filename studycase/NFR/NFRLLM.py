import ollama
import textwrap
import pandas as pd
import json

models = ["mistral-nemo"]

def serialize_response(response: str) -> dict:
    try:
        if hasattr(response, 'response'):
            return {"response": response.response}
        return {"raw_response": str(response)}
    except Exception as e:
        return {"error": str(e), "raw_response": str(response)}

def run_llm(message: str, prompt: str) -> dict:
    full_prompt = textwrap.dedent(f"""

    \"\"\"{message.get('description', '')}\"\"\"

    {prompt}

    You MUST return ONLY a JSON object with EXACTLY the following structure, without any additional text or whitespace/newlines/tabs:
    The answer must be in English!
    IMPORTANT: Do not include explanations, additional text, or any special characters. Return ONLY the JSON in a single line.
        """)  

    response = ollama.generate(
        model=models[0],
        prompt=full_prompt,
        format="json"
    )

    return serialize_response(response)

def get_prompt(prompt_name: str) -> str:
    with open(f"NFR/prompts/{prompt_name}.txt", "r", encoding="utf-8") as file:
        return file.read()

def read_data(file_name: str, columns: list = None) -> pd.DataFrame:
    """
    Generalized function to read data from CSV and return selected columns.
    """
    data = pd.read_csv(f"NFR/datas/{file_name}.csv")
    if columns:
        return data[columns]
    return data

def save_response(results: list, file_name: str):
    with open(f"NFR/results/{file_name}.json", "w", encoding="utf-8") as file:
        for result in results:
            file.write(json.dumps(result) + "\n")

def normalize_data(data: dict) -> dict:
    return json.loads(json.dumps(data, ensure_ascii=False))

def analyze_data(data_name: str, description_column: str):
    """
    Generalized function to analyze data from any source (Jira, GitHub).
    """
    print(f"\n🔄 Starting data analysis for: {data_name}")
    prompt = get_prompt(data_name)
    print(f"✅ Prompt successfully loaded from: NFR/prompts/{data_name}.txt")
    
    data = read_data(data_name, [description_column])
    print(f"📊 Data loaded: {len(data)} records found\n")
    
    results = []
    
    for index, row in data.iterrows():
        structured_data = normalize_data(row.to_dict())
        print(f"🔍 Processing item {index + 1}/{len(data)}")
        print("📝 Item data:")
        print(json.dumps(structured_data, indent=2, ensure_ascii=False))
        
        try:
            response = run_llm(structured_data, prompt)
            print("✨ Response obtained:")
            print(json.dumps(response, indent=2, ensure_ascii=False) + "\n")
            results.append(response)
        except Exception as e:
            print(f"❌ Error processing item {index}: {str(e)}\n")
    
    print(f"\n💾 Saving {len(results)} results...")
    save_response(results, data_name)
    print(f"✅ Analysis completed! Results saved in: NFR/results/{data_name}_2.json")

def analyze_github_commits():
    """
    Function to analyze commit messages and related diffs from GitHub.
    """
    print("\n🔄 Starting analysis of non-functional requirements in GitHub")
    
    commits_data = read_data("commits", ["message", "id"])
    modified_files_data = read_data("modified_file", ["commit_id", "diff"])
    print(f"📊 Commit data loaded: {len(commits_data)} records found")
    print(f"📊 Modified file data loaded: {len(modified_files_data)} records found")
    
    results = []
    
    for index, commit_row in commits_data.iterrows():
        commit_message = commit_row['message']
        commit_id = commit_row['id']
        
        related_files = modified_files_data[modified_files_data['commit_id'] == commit_id]
        
        if related_files.empty:
            print(f"❌ No modified files found for commit ID: {commit_id}")
            continue
        
        for _, file_row in related_files.iterrows():
            file_diff = file_row['diff']
            
            structured_data = {
                "description": f"Commit: {commit_message}\nDiff: {file_diff}"
            }
            
            print(f"🔍 Processing commit {commit_id} and file diff")
            print("📝 Item data:")
            print(json.dumps(structured_data, indent=2, ensure_ascii=False))
            
            try:
                response = run_llm(structured_data, get_prompt("github"))
                print("✨ Response obtained:")
                print(json.dumps(response, indent=2, ensure_ascii=False) + "\n")
                results.append(response)
            except Exception as e:
                print(f"❌ Error processing commit {commit_id}: {str(e)}\n")
    
    print(f"\n💾 Saving {len(results)} results...")
    save_response(results, "github_results")
    print(f"✅ Analysis completed! Results saved in: NFR/results/github_2.json")

def main():
    analyze_github_commits()
    analyze_data("jira", "description")
    
if __name__ == "__main__":
    main()