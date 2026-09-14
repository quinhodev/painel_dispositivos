# Painel de Gestão de Dispositivos

Projeto — painel simples para cadastro e monitoramento de dispositivos (players/telas), inspirado em sistemas de gestão de sinalização digital.

## Stack

- **Back-end:** Python + FastAPI + SQLAlchemy
- **Banco de dados:** SQLite (arquivo `dispositivos.db`, criado automaticamente)
- **Front-end:** HTML + CSS + JavaScript puro (consome a API via `fetch`)

## Como rodar

### 1. Back-end

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. Documentação automática (Swagger) em `http://127.0.0.1:8000/docs` — ótimo para mostrar no vídeo de entrega.

### 2. Front-end

Basta abrir `frontend/index.html` no navegador (duplo clique, ou com a extensão "Live Server" do VS Code). Ele já aponta para `http://127.0.0.1:8000`.

## Funcionalidades implementadas

- [x] Cadastro de dispositivo (nome + local)
- [x] Listagem de dispositivos
- [x] Remoção de dispositivo
- [x] Filtro por local, status e busca por nome
- [x] Endpoint de "heartbeat" (simula dispositivo reportando status online)
- [x] Resumo/dashboard (total, online, offline, % online)

## Estrutura

```
painel-dispositivos/
├── backend/
│   ├── main.py          # rotas da API
│   ├── models.py        # modelo do banco (SQLAlchemy)
│   ├── schemas.py        # validação de entrada/saída (Pydantic)
│   ├── database.py       # conexão com o SQLite
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── BOARD.md              # lista de funcionalidades por sprint (AC1–Final)
```

## Próximos passos (ver BOARD.md)

Autenticação simples e exportação de relatório, previstos para a entrega final.
