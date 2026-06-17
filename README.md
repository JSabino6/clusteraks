# AKS Python Demo

Aplicacao Python simples para demonstrar:

- AKS rodando uma aplicacao.
- PostgreSQL rodando como StatefulSet.
- Aplicacao com uma replica.
- Aplicacao conectando no banco e persistindo dados.

## Documentacao

- `DOCUMENTACAO_PROJETO.md`: explicacao completa do projeto, arquitetura e recursos criados.


## Rodar local com Docker

```bash
docker build -t aks-python-demo:local .
docker run --rm -p 5000:5000 aks-python-demo:local
```

Para rodar em um local conectado a um banco, suba um PostgreSQL e configure as variaveis `DB_HOST`, `DB_NAME`, `DB_USER` e `DB_PASSWORD`.

## Subir no AKS

Crie um Azure Container Registry, envie a imagem, troque a imagem no `k8s.yaml` e aplique:

```bash
kubectl apply -f k8s.yaml
kubectl get pods
kubectl get svc
```
