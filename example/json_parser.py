import json

def read_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)
    
if __name__ == "__main__":
    file_path = "esp8266_Arduino_issues.json"
    data = read_json(file_path)

    print(f'Total de issues: {len(data)}')
    
    for issue in data:
        print(f'{issue["number"]} - {issue["created_at"]}')





