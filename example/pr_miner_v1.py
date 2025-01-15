from github import Github
from datetime import datetime
import pytz
from dotenv import load_dotenv
import os
import concurrent.futures
from tqdm import tqdm

load_dotenv()

def process_pull_requests(pulls, start_date, end_date):
    filtered_pulls = []
    
    with tqdm(total=pulls.totalCount, desc="Processando PRs") as pbar:
        for pull in pulls:
            if start_date <= pull.created_at <= end_date:
                filtered_pulls.append({
                    'number': pull.number,
                    'title': pull.title,
                    'created_at': pull.created_at,
                    'state': pull.state,
                    'user': pull.user.login if pull.user else None,
                    'merged': pull.merged,
                    'comments': pull.comments,
                    'commits': pull.commits,
                    'additions': pull.additions,
                    'deletions': pull.deletions,
                    'changed_files': pull.changed_files
                })
            pbar.update(1)
    
    return filtered_pulls

def main():
    g = Github(os.getenv("GITHUB_TOKENS"))
    repo = g.get_repo("elastic/elasticsearch")
    
    start_date = datetime(2000, 1, 1, tzinfo=pytz.UTC)
    end_date = datetime(2025, 2, 2, tzinfo=pytz.UTC)
    
    # Obtém todos os PRs de uma vez
    pulls = repo.get_pulls(state="all")
    
    # Processa os PRs
    filtered_pulls = process_pull_requests(pulls, start_date, end_date)
    
    # Imprime os resultados
    print(f"\nTotal de PRs encontrados: {len(filtered_pulls)}")
    for pr in filtered_pulls:
        print(f"{pr['number']} - {pr['title']} - {pr['created_at']}")
        print(f"  Estado: {pr['state']}")
        print(f"  Autor: {pr['user']}")
        print(f"  Merged: {pr['merged']}")
        print(f"  Comentários: {pr['comments']}")
        print(f"  Commits: {pr['commits']}")
        print(f"  Alterações: +{pr['additions']} -{pr['deletions']} em {pr['changed_files']} arquivos")
        print("-" * 80)

if __name__ == "__main__":
    main()
