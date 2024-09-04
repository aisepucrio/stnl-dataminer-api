-- Criar o esquema se ele não existir
CREATE SCHEMA IF NOT EXISTS aisepucrio_stnl_featuresmining;

-- Criação da tabela principal particionada no esquema desejado
CREATE TABLE IF NOT EXISTS aisepucrio_stnl_featuresmining.repositorios (
    id SERIAL,
    nome VARCHAR(255),
    ssh_url VARCHAR(255),
    tipo_mineracao VARCHAR(50),
    dados JSONB,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tamanho BIGINT,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    num_commits INT,
    PRIMARY KEY (id, tipo_mineracao)  -- Chave primária agora inclui a coluna de partição
) PARTITION BY LIST (tipo_mineracao);



-- Partições
-- Criação da partição de código
CREATE TABLE IF NOT EXISTS aisepucrio_stnl_featuresmining.repositorios_codigo PARTITION OF aisepucrio_stnl_featuresmining.repositorios
FOR VALUES IN ('codigo');

-- Criação da partição de documentação
CREATE TABLE IF NOT EXISTS aisepucrio_stnl_featuresmining.repositorios_doc PARTITION OF aisepucrio_stnl_featuresmining.repositorios
FOR VALUES IN ('doc');

-- Criação da partição de commits
CREATE TABLE IF NOT EXISTS aisepucrio_stnl_featuresmining.repositorios_commits PARTITION OF aisepucrio_stnl_featuresmining.repositorios
FOR VALUES IN ('commits');



-- Índices
-- Índice para tipo de mineração
CREATE INDEX idx_tipo_mineracao ON aisepucrio_stnl_featuresmining.repositorios(tipo_mineracao);

-- Índice para URL SSH do repositório
CREATE INDEX idx_ssh_url ON aisepucrio_stnl_featuresmining.repositorios(ssh_url);

-- Índices para datas
CREATE INDEX idx_data_criacao ON aisepucrio_stnl_featuresmining.repositorios(data_criacao);
CREATE INDEX idx_ultima_atualizacao ON aisepucrio_stnl_featuresmining.repositorios(ultima_atualizacao);
