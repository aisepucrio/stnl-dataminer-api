import ollama
import textwrap
import pandas as pd
import json

models = ["mistral-small:24b", "gemma3:27b"]

def serialize_response(response: str) -> dict:
    try:
        if hasattr(response, 'response'):
            return {"response": response.response}
        return {"raw_response": str(response)}
    except Exception as e:
        return {"error": str(e), "raw_response": str(response)}

def run_llm(message: str, prompt: str, data_name: str) -> dict:

    print(f'\nmessage: {message}\n')

    if data_name == "commits":
        message = message['message']

    full_prompt = textwrap.dedent(f"""

\"\"\"{message}\"\"\"

{prompt}

You MUST return ONLY a JSON object with EXACTLY the following structure, without any additional text or whitespace/newlines/tabs:

{{"sentiment": "positive/negative/neutral", "confidence": "value between 0 and 1"}}

IMPORTANT: Do not include explanations, additional text, or any special characters. Return ONLY the JSON in a single line.
    """)

    prompt = full_prompt

    response = ollama.generate(
        model=models[1],
        prompt=prompt,
        format="json"
    )

    return serialize_response(response)

def get_prompt(prompt_name: str) -> str:
    with open(f"studycase/sentiment/prompts/{prompt_name}.txt", "r", encoding="utf-8") as file:
        return file.read()
    
def read_data(file_name: str) -> str:
    data = pd.read_csv(f"studycase/sentiment/data/{file_name}.csv")
    
    if file_name == "commits":
        relevant_columns = ["message"]
        return data[relevant_columns]
    elif file_name == "Issues&PRs":
        relevant_columns = ["title", "body", "comments", "reactions"]
        return data[relevant_columns]
    elif file_name == "jira":
        relevant_columns = ["issuetype_description", "summary", "description", "commits"]
        return data[relevant_columns]
    
def save_response(results: list, file_name: str):
    with open(f"studycase/sentiment/results/{file_name}.json", "w", encoding="utf-8") as file:
        for result in results:
            file.write(json.dumps(result) + "\n")

def normalize_data(data: dict) -> dict:
    return json.loads(json.dumps(data, ensure_ascii=False))

def analyze_sentiment(data_name):
    print(f"\n🔄 Starting sentiment analysis for: {data_name}")
    prompt = get_prompt(data_name)
    print(f"✅ Prompt successfully loaded from: studycase/sentiment/prompts/{data_name}.txt")
                                                                                                                    
    data = read_data(data_name)
    print(f"📊 Data loaded: {len(data)} records found\n")
    results = []

    for index, row in data.iterrows():
        structured_data = normalize_data(row.to_dict())
        print(f"🔍 Processing item {index + 1}/{len(data)}")
        print("📝 Item data:")
        print(json.dumps(structured_data, indent=2, ensure_ascii=False))
        
        try:
            response = run_llm(structured_data, prompt, data_name)
            print("✨ Response obtained:")
            print(json.dumps(response, indent=2, ensure_ascii=False) + "\n")
            results.append(response)
        except Exception as e:
            print(f"❌ Error processing item {index}: {str(e)}\n")
    
    print(f"\n💾 Saving {len(results)} results...")
    save_response(results, data_name)
    print(f"✅ Analysis completed! Results saved in: studycase/sentiment/results/{data_name}.json")

def main():
    analyze_sentiment("jira")
    # for data_name in ["commits", "Issues&PRs", "jira"]:
    #     analyze_sentiment(data_name)

if __name__ == "__main__":
    main()
