# Arquitetura stnl-dataminer-api

## App: task-queue

### Modelos

#### Task

##### Campos

- status: CharField (e.g., "pending", "in_progress", "completed", "failed") - Usar model.TextChoices para limitar para esses valores
- created_at: DateTimeField
- updated_at: DateTimeField
- metadata: JSONField (Campo para informar os metadados que serão utilizados para definir se uma tarefa é duplicada e como ela deve ser executada)
- depends_on: ForeignKey (chave estrangeira para o próprio modelo)

##### Rotas

- /task/ (GET) - Retorna o status de uma tarefa
- /task/<id> (DELETE) - Cancela uma tarefa (não deleta o registro no banco, apenas seta como failed)

##### Outros detalhes de implementação

Toda a lógica de criação de uma tarefa, cuidando para que tarefas duplicadas não sejam executadas, deve ser feita com a criação de um objeto Manager do django.

Usando esse tipo de objeto, o django permite que seja sobrescrito o Model.objects, permitindo a criação de algo semelhante a `Task.objects.create_task(...)`

Esse método deve utilizar o celery para gerenciar a fila de tarefas.

Lembrando, esse app é pra ser completamente desacoplado de qualquer outro app (e.g., github, JIRA). Quem for utilizar é que vai chamar, ele só chama o celery.

Sugestão: A função com o comando que será executado aqui deve ser passada como parâmetro, e os parâmetros para aquela função como outro parâmetro (pode ser dicionário, ou usando *args e **kwargs).

```python
Ex: create_task(command_func, *args, **kwargs):
        rodar_usando_celery(command_func, *args, **kwargs)
```

### App: github

#### Modelos

Já definidos. Só sugiro mudar o commit para ser uma chave estrangeira para o app git (ou pydriller), que está definido abaixo.

#### Rotas

- /github/ (GET) - Lista todas as possibilitades de coleta para o Github, e possiveis opções (definir formato padronizado para o sistema inteiro).

OBS: DEIXAR ESSA ROTA POR ÚLTIMO. ESSA ROTA SERÁ COMO SE FOSSE A "COLA" QUE VAI DEIXAR O SISTEMA GENÉRICO DEPOIS QUE IMPLEMENTARMOS OS COLETORES.

Exemplo de estrutura (provisória, apenas para fim de exemplo, não usar, faltam campos):

```json
{
    "data_types": [
        {
            "name": "Pull requests",
            "url": "/pr",
            "options": [
                {
                    "name": "exclude_fields",
                    "descriptions": "List of fields to be excluded when collecting data."
                }
            ]
        },
        {
            "name": "Commits",
            "url": "/commits/"
        }
    ]
}
```


- /github/pr/\<project> (GET) - Lista todas as PRs para um projeto
- /github/pr/\<project> (POST) - Inicia uma coleta de PRs para esse
- projeto (com filtros, data, hash, etc...)
- /github/pr/\<project>/\<id> (GET) - Pega uma PR específica de um projeto
- /github/pr/\<project>/\<id> (POST) - Inicia a coleta de uma PR específica
- /github/pr/\<project>/\<id> (DELETE) - Remove uma PR já coletada do banco.

A omissão de uma rota de atualização é proposital. Essa atualização apenas deve ocorrer se alguém pedir uma nova coleta que inclui novas informações sobre um item já existente no banco. Por isso, esse tratamento deve ocorrer nas rotas POST.

Fazer o mesmo para commits, issues e quaisquer outras coisas que forem ser coletadas.

#### Tasks

Arquivo tasks.py, dentro do app, com as funções que executam e criam as tarefas para as coletas dos github, gerenciando os metadados e modelos apropriadamente.

### App: git ou pydriller

Esse app representará os dados do pydriller. Ele terá apenas modelos, e um arquivo tasks.py, que definirá as coletas que serão feitas via pydriller.

#### Modelos

A definir, representando as informações que são coletáveis via pydriller.

### JIRA

Seguir o mesmo modelo do app do github.
