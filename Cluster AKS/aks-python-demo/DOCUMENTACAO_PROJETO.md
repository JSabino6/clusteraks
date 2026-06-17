# Documentação do projeto - Aplicação Python no AKS com banco em StatefulSet

## Visão geral

Este projeto foi feito como uma atividade prática para subir uma aplicação em um cluster Kubernetes gerenciado pela Azure, usando o Azure Kubernetes Service, mais conhecido como AKS.

A ideia principal foi montar um ambiente simples, mas que mostrasse pontos importantes de uma implantação real:

- uma aplicação em Python;
- um banco de dados separado da aplicação;
- o banco rodando como StatefulSet;
- a aplicação rodando com uma réplica;
- comunicação entre aplicação e banco dentro do cluster;
- exposição da aplicação para acesso externo;
- imagem Docker armazenada em um registry da Azure.

Para a aplicação, foi criada uma API simples em Python usando Flask. A API permite cadastrar e listar itens. Esses itens são gravados em um banco PostgreSQL, então ela não é só uma aplicação "estática": ela realmente depende do banco para funcionar.

O banco PostgreSQL foi colocado em um StatefulSet, porque banco de dados precisa manter estado. Diferente de uma aplicação comum, que pode ser apagada e recriada sem perder informação, o banco precisa de armazenamento persistente. Por isso, junto com o StatefulSet, foi criado também um volume persistente usando `volumeClaimTemplates`.

## Arquitetura usada

A arquitetura final ficou assim:

```text
Usuário
  |
  | HTTP
  v
Service LoadBalancer: python-api
  |
  v
Deployment: python-api
  |
  | conexão interna na porta 5432
  v
Service interno: postgres
  |
  v
StatefulSet: postgres
  |
  v
Persistent Volume Claim: postgres-data
```

O usuário acessa a aplicação pelo IP externo criado pelo Service do tipo `LoadBalancer`. A aplicação não acessa o banco por IP fixo, e sim pelo nome do Service interno `postgres`. Isso é importante porque no Kubernetes os pods podem ser recriados e trocar de IP. Usando Service, a aplicação sempre consegue encontrar o banco pelo mesmo nome.

## Recursos principais criados

### Cluster AKS

O cluster AKS foi criado no resource group:

```text
rg-aks-estagio
```

Com o nome:

```text
aks-estagio
```

O AKS é o serviço gerenciado de Kubernetes da Azure. Em vez de instalar e administrar um cluster Kubernetes manualmente, a Azure cuida de boa parte da infraestrutura do cluster. Mesmo assim, os recursos Kubernetes, como Pods, Deployments, Services e StatefulSets, continuam sendo criados com `kubectl`.

### Azure Container Registry

Também foi usado um Azure Container Registry, neste caso:

```text
acrjoaoestagio23178.azurecr.io
```

Ele serve para armazenar a imagem Docker da aplicação Python. O AKS precisa conseguir baixar essa imagem quando for criar o pod da aplicação. Por isso o AKS foi ligado ao ACR com o comando `az aks update --attach-acr`.

### Aplicação Python

A aplicação está no arquivo:

```text
app.py
```

Ela usa Flask para criar uma API HTTP. Os principais endpoints são:

```text
GET /
GET /health
GET /items
POST /items
```

O endpoint `/` retorna uma mensagem básica dizendo que a aplicação está rodando. O endpoint `/health` é usado pelas probes do Kubernetes para verificar se o container está saudável. O endpoint `/items` é o mais importante para a demonstração, porque ele grava e lê dados do PostgreSQL.

Quando a aplicação inicia, ela tenta se conectar ao banco e cria a tabela `items`, caso ela ainda não exista. Isso foi feito para simplificar a demonstração, evitando a necessidade de rodar scripts manuais de criação de tabela.

A tabela criada é:

```sql
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
```

Ou seja, cada item gravado tem um identificador, um nome e a data de criação.

### Dockerfile

O arquivo `Dockerfile` empacota a aplicação Python em uma imagem Docker.

Ele usa a imagem base:

```text
python:3.12-slim
```

Depois copia o arquivo `requirements.txt`, instala as dependências e copia o código da aplicação. No final, a aplicação é iniciada com Gunicorn:

```text
gunicorn --bind 0.0.0.0:5000 app:app
```

O Gunicorn foi usado porque é mais adequado para rodar Flask em container do que o servidor de desenvolvimento padrão do Flask.

## Explicação do arquivo k8s.yaml

O arquivo `k8s.yaml` concentra os recursos Kubernetes usados no projeto.

### Secret do PostgreSQL

O primeiro recurso é um Secret:

```yaml
kind: Secret
metadata:
  name: postgres-secret
```

Ele guarda as informações de conexão do banco:

- nome do banco;
- usuário;
- senha.

Esses valores são usados tanto pelo container do PostgreSQL quanto pela aplicação Python.

Em um ambiente real, a senha não deveria ficar escrita diretamente no arquivo YAML. Para a atividade, isso foi mantido simples para facilitar a apresentação e o entendimento.

### Service interno do PostgreSQL

Depois foi criado um Service chamado:

```text
postgres
```

Ele é usado pela aplicação para encontrar o banco dentro do cluster.

O Service foi criado com:

```yaml
clusterIP: None
```

Esse formato é comum com StatefulSet, porque cria um Service headless. Ele ajuda o Kubernetes a manter uma identidade de rede mais estável para os pods do StatefulSet.

### StatefulSet do PostgreSQL

O banco roda como:

```yaml
kind: StatefulSet
metadata:
  name: postgres
```

Foi configurada uma réplica:

```yaml
replicas: 1
```

Para a atividade, uma réplica é suficiente. O ponto principal era mostrar que o banco está em StatefulSet e possui volume persistente.

O container usa a imagem:

```text
postgres:16
```

Também foi definida a variável:

```yaml
PGDATA: /var/lib/postgresql/data/pgdata
```

Isso evita alguns problemas comuns quando o PostgreSQL inicializa em volumes persistentes montados pelo Kubernetes.

### Volume persistente

O StatefulSet cria um volume por meio de:

```yaml
volumeClaimTemplates
```

Neste projeto, foi solicitado um volume de:

```text
5Gi
```

Esse volume fica montado em:

```text
/var/lib/postgresql/data
```

É ali que o PostgreSQL grava os dados. Se o pod do banco for recriado, os dados continuam no volume.

### Deployment da aplicação Python

A aplicação roda como Deployment:

```yaml
kind: Deployment
metadata:
  name: python-api
```

Ela foi configurada com:

```yaml
replicas: 1
```

Isso atende ao requisito de ter uma réplica da aplicação.

A imagem usada foi:

```text
acrjoaoestagio23178.azurecr.io/aks-python-demo:1.0
```

Essa imagem foi gerada localmente com Docker e enviada para o Azure Container Registry.

A aplicação recebe as informações do banco por variáveis de ambiente:

```text
DB_HOST=postgres
DB_PORT=5432
DB_NAME
DB_USER
DB_PASSWORD
```

O `DB_HOST` aponta para o Service interno do PostgreSQL. Já nome do banco, usuário e senha vêm do Secret.

### Readiness e liveness probes

No Deployment também foram configuradas probes:

```yaml
readinessProbe
livenessProbe
```

As duas consultam:

```text
/health
```

A readiness probe indica quando a aplicação está pronta para receber tráfego. A liveness probe ajuda o Kubernetes a saber se a aplicação continua viva. Se a aplicação travar, o Kubernetes pode reiniciar o container automaticamente.

### Service externo da aplicação

Para acessar a aplicação de fora do cluster, foi criado um Service:

```yaml
kind: Service
metadata:
  name: python-api
spec:
  type: LoadBalancer
```

O tipo `LoadBalancer` faz a Azure criar um IP externo. Foi por esse IP que a aplicação pôde ser testada com `curl`.

## Testes realizados

Após aplicar o manifesto no cluster, foram usados comandos para verificar se os recursos estavam rodando:

```bash
kubectl get pods
kubectl get statefulset
kubectl get pvc
kubectl get deployment
kubectl get svc
```

Também foi testado o endpoint da aplicação com:

```powershell
curl.exe "http://52.224.81.255/"
```

E foi enviado um item para a API:

```powershell
curl.exe -X POST "http://52.224.81.255/items" -H "Content-Type: application/json" --data "{""name"":""teste do estagio""}"
```

Depois, os dados podem ser consultados com:

```powershell
curl.exe "http://52.224.81.255/items"
```

Esse teste mostra que a aplicação está acessível externamente e que ela consegue gravar e ler dados do banco PostgreSQL que está dentro do cluster.

## Como explicar o projeto em uma apresentação

Uma forma simples de apresentar seria:

> Eu criei um cluster Kubernetes na Azure usando AKS. Depois criei uma aplicação Python com Flask, gerei uma imagem Docker e publiquei essa imagem no Azure Container Registry. No Kubernetes, subi a aplicação como um Deployment com uma réplica e subi o PostgreSQL como StatefulSet, porque o banco precisa manter estado e usar volume persistente. A aplicação acessa o banco pelo Service interno `postgres` e é exposta para fora do cluster por um Service do tipo LoadBalancer.

Também é interessante mostrar estes comandos durante a apresentação:

```bash
kubectl get deployment python-api
kubectl get statefulset postgres
kubectl get pvc
kubectl get svc python-api
```

Eles provam os pontos principais:

- a aplicação existe e está rodando;
- o banco está em StatefulSet;
- existe volume persistente;
- a aplicação está exposta por IP externo.

## Observação sobre custos

Enquanto o cluster AKS estiver ligado, pode haver cobrança de recursos da Azure, principalmente:

- máquina virtual do node;
- disco persistente do banco;
- LoadBalancer;
- armazenamento do Container Registry.

Para parar temporariamente:

```bash
az aks stop --resource-group rg-aks-estagio --name aks-estagio
```

Para iniciar novamente:

```bash
az aks start --resource-group rg-aks-estagio --name aks-estagio
```

Para apagar tudo quando não for mais necessário:

```bash
az group delete --name rg-aks-estagio --yes --no-wait
```

Esse último comando remove o resource group inteiro, então só deve ser usado quando a atividade estiver finalizada.
