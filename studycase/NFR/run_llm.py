import ollama
import textwrap
import json

# Nome do modelo
MODEL = "gemma3:27b"

# Prompt fixo para classificação de sentimento de requisitos
SENTIMENT_PROMPT = """
You are a software engineering expert specialized in requirements analysis.
Analyze the sentiment expressed in the following non-functional requirement:

\"\"\"{nfr}\"\"\"

Classify the sentiment as one of: "positive", "neutral", or "negative".
Then give a confidence score between 0 and 1.

You MUST return ONLY a JSON object with EXACTLY the following structure, in a single line:

{{"sentiment": "positive/negative/neutral", "confidence": "value between 0 and 1"}}

Do not include explanations, comments, or extra characters.
"""

def serialize_response(response) -> dict:
    try:
        if hasattr(response, 'response'):
            return json.loads(response.response)
        return json.loads(str(response))
    except Exception as e:
        return {"error": str(e), "raw_response": str(response)}

def run_sentiment_analysis(nfr_text: str) -> dict:
    prompt = textwrap.dedent(SENTIMENT_PROMPT.format(nfr=nfr_text.strip()))

    response = ollama.generate(
        model=MODEL,
        prompt=prompt,
        format="json"
    )

    return serialize_response(response)

def analyze_nfr_sentiment_from_json(input_path: str, output_path: str, field_name: str = "nfr"):
    with open(input_path, "r", encoding="utf-8") as infile:
        data = [json.loads(line) for line in infile if line.strip()]

    enriched_data = []

    for idx, item in enumerate(data):
        nfr_text = item.get(field_name, "").strip()
        print(f"\n🔍 Analisando NFR {idx + 1}/{len(data)}:")
        print(nfr_text)

        try:
            result = run_sentiment_analysis(nfr_text)
            print(f"✨ Resultado: {result}")
            item["sentiment"] = result.get("sentiment", "error")
            item["confidence"] = result.get("confidence", None)
        except Exception as e:
            print(f"❌ Erro: {e}")
            item["sentiment"] = "error"
            item["confidence"] = None

        enriched_data.append(item)

    with open(output_path, "w", encoding="utf-8") as outfile:
        for entry in enriched_data:
            outfile.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n✅ Análise concluída! Resultados salvos em: {output_path}")

def main():
    input_path = fr"C:\Users\breno\OneDrive\Documentos\GitHub\stnl-dataminer-api\studycase\NFR\data\github_results.json"  # um JSON com uma lista de objetos
    output_path = fr"C:\Users\breno\OneDrive\Documentos\GitHub\stnl-dataminer-api\studycase\NFR\data\nfrs_sentiment.json"
    analyze_nfr_sentiment_from_json(input_path, output_path)

if __name__ == "__main__":
    main()
