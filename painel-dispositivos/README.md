# Painel de Gestão de Dispositivos

Projeto — painel simples para cadastro e monitoramento de dispositivos (players/telas), inspirado em sistemas de gestão de sinalização digital.

## Stack

- **Back-end:** Python + FastAPI + SQLAlchemy
- **Banco de dados:** SQLite (arquivo `dispositivos.db`, criado automaticamente)
- **Front-end:** HTML + CSS + JavaScript puro (consome a API via `fetch`)

## Como rodar

### 1. Back-end

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. Documentação automática (Swagger) em `http://127.0.0.1:8000/docs` — ótimo para mostrar no vídeo de entrega.

### 2. Front-end

Basta abrir `frontend/index.html` no navegador (duplo clique, ou com a extensão "Live Server" do VS Code). Ele já aponta para `http://127.0.0.1:8000`.

## Funcionalidades implementadas

**AC1**

- [x] Cadastro de dispositivo (nome + local)
- [x] Listagem de dispositivos
- [x] Remoção de dispositivo
- [x] Tratamento de erro no front-end (faixa vermelha quando a API falha)

**AC2 — Organização e busca**

- [x] Filtro por local (opções vindas de `GET /locais`)
- [x] Busca por nome
- [x] Filtro por status (online/offline)
- [x] Ordenação por coluna (clique no cabeçalho; clicar de novo inverte a direção)

**Planejado**

- [ ] AC3: endpoint de heartbeat e "há quanto tempo" da última sincronização
- [ ] Entrega final: autenticação, exportação CSV, dashboard e polimento

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/dispositivos` | Lista. Parâmetros opcionais: `local`, `status`, `busca`, `ordenar_por`, `direcao` |
| GET | `/locais` | Locais distintos cadastrados (alimenta o filtro) |
| POST | `/dispositivos` | Cadastra (`nome`, `local`) |
| DELETE | `/dispositivos/{id}` | Remove |

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

AC3 (heartbeat e monitoramento) e, na entrega final, autenticação simples, exportação de relatório e dashboard.
