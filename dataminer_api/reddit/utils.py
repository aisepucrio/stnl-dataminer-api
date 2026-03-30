from typing import Dict, List, Any
import csv

def save_dicts_to_csv(rows: List[Dict[str, Any]], filename: str) -> None:
    if not rows:
        print(f"Nenhuma linha para salvar em {filename}.")
        return
    fieldnames = list(rows[0].keys())
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Arquivo salvo: {filename} (linhas: {len(rows)})")
    