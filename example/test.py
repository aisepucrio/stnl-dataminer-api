import requests
from bs4 import BeautifulSoup

def get_contributors_from_html(owner: str, repo: str):
    """
    Obtém o número de contribuidores de um repositório GitHub através do HTML da página
    
    Args:
        owner (str): Nome do proprietário do repositório
        repo (str): Nome do repositório
        
    Returns:
        int|None: Número de contribuidores ou None se não for possível obter
    """
    url = f'https://github.com/{owner}/{repo}'
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'lxml')
        contributors_element = soup.find('a', {'href': f'/{owner}/{repo}/graphs/contributors'})
        if contributors_element:
            span_element = contributors_element.find('span', class_='Counter ml-1')
            if span_element and 'title' in span_element.attrs:
                try:
                    return int(span_element['title'].replace(',', ''))
                except ValueError:
                    return None
    return None

print(get_contributors_from_html('grafana', 'grafana'))