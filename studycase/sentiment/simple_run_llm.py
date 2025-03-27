import ollama
import textwrap
import pandas as pd
import json

def serialize_response(response: str) -> dict:
    try:
        if hasattr(response, 'response'):
            return {"response": response.response}
        return {"raw_response": str(response)}
    except Exception as e:
        return {"error": str(e), "raw_response": str(response)}

def run_llm(message: str, prompt: str) -> dict:
    prompt = textwrap.dedent(f"""j

        \"\"\"{message}\"\"\"

        {prompt}

        Return your response in the following JSON format without deviations:

        {{
            "sentiment": "positive/negative/neutral",
            "confidence": "value between 0 and 1"
        }}
    """)

    response = ollama.generate(
        model="mistral-small:24b",
        prompt=prompt,
        format="json"
    )

    return serialize_response(response)

def get_prompt(prompt_name: str) -> str:
    with open(f"analysis/sentiment/prompts/{prompt_name}.txt", "r", encoding="utf-8") as file:
        return file.read()
    
def read_data(file_name: str) -> str:
    data = pd.read_csv(f"analysis/data/{file_name}.csv")
    
    if file_name == "commits":
        relevant_columns = ["message"]
        return data[relevant_columns]
    elif file_name == "Issues&PRs":
        relevant_columns = ["title", "body", "comments", "reactions"]
        return data[relevant_columns]
    elif file_name == "jira":
        relevant_columns = ["issuetype_description","summary", "description", "commits"]
        return data[relevant_columns]
    
def save_response(results: list, file_name: str):
    with open(f"analysis/sentiment/results/{file_name}.json", "w", encoding="utf-8") as file:
        for result in results:
            file.write(json.dumps(result) + "\n")

def normalize_data(data: dict) -> dict:
    return json.loads(json.dumps(data, ensure_ascii=False))

def main(data_name):
    print(f"\n🔄 Iniciando análise de sentimento para: {data_name}")
    prompt = get_prompt(data_name)
    print(f"✅ Prompt carregado com sucesso de: analysis/sentiment/prompts/{data_name}.txt")
                                                                                                                    
    data = read_data(data_name)
    print(f"📊 Dados carregados: {len(data)} registros encontrados\n")
    results = []

    for index, row in data.iterrows():
        structured_data = normalize_data(row.to_dict())
        print(f"🔍 Processando item {index + 1}/{len(data)}")
        print("📝 Dados do item:")
        print(json.dumps(structured_data, indent=2, ensure_ascii=False))
        
        try:
            response = run_llm(structured_data, prompt)
            print("✨ Resposta obtida:")
            print(json.dumps(response, indent=2, ensure_ascii=False) + "\n")
            results.append(response)
        except Exception as e:
            print(f"❌ Erro ao processar item {index}: {str(e)}\n")
    
    print(f"\n💾 Salvando {len(results)} resultados...")
    save_response(results, data_name)
    print(f"✅ Análise concluída! Resultados salvos em: analysis/sentiment/results/{data_name}.json")

if __name__ == "__main__":
    main("jira")