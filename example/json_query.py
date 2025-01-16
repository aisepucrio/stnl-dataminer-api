import json

label = '>test'

def query_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    total_prs = len(data["pull_requests"])
    print(f'\nTotal de PRs: {total_prs}\n')

    count_with_label = 0
    count_without_label = 0

    for pr in data['pull_requests']:
        if label in pr['labels']:
            print(f'\nPR com label {label}:\n')
            print(f'{pr["number"]} - {pr["title"]}\n')
            count_with_label += 1
        else:
            print(f'PR sem label {label}')
            count_without_label += 1

    print(f'\nTotal de PRs com label {label}: {count_with_label}\n')
    print(f'Total de PRs sem label {label}: {count_without_label}\n')

    return None

if __name__ == "__main__":
    result = query_json("elasticsearch_prs.json")
