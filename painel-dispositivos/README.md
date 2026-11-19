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

### 3. Login

O painel exige login. Credenciais padrão (projeto acadêmico local):

- **Usuário:** `admin`
- **Senha:** `admin123`

Para trocar sem mexer no código, defina as variáveis de ambiente antes de subir o back-end:

```powershell
$env:PAINEL_USUARIO = "meu_usuario"
$env:PAINEL_SENHA = "minha_senha"
python -m uvicorn main:app --reload
```

O login é guardado só na memória do servidor: reiniciar o `uvicorn` (inclusive pelo `--reload` ao salvar um arquivo) exige entrar de novo. No Swagger (`/docs`), use o botão **Authorize** com o token devolvido por `POST /login`.

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

**AC3 — Status e monitoramento**

- [x] Endpoint de heartbeat (`POST /dispositivos/{id}/heartbeat`): o dispositivo avisa que está ativo e vira online
- [x] Botão "Heartbeat" na tela, simulando o dispositivo reportando atividade
- [x] Indicador de "há quanto tempo" desde a última sincronização (atualiza a cada segundo, com cor verde/âmbar/vermelha)
- [x] Marcação automática como offline sem heartbeat (padrão: 1 minuto, ajustável em `TEMPO_LIMITE_MINUTOS`)
- [x] Atualização automática da lista a cada 10 segundos

**Entrega final — Refinamento**

- [x] Autenticação simples: login com token (`POST /login`), todas as rotas protegidas, botão "Sair" (`POST /logout`)
- [x] Dashboard com métricas no topo: total, online, offline e % online (`GET /dashboard/resumo`)
- [x] Exportação de relatório em CSV (`GET /relatorio/csv`), respeitando os filtros e a ordenação da tela
- [x] Polimento: tela de login, proteção contra HTML injetado nos nomes, relatório protegido contra fórmulas de planilha e ajustes visuais
- [x] Roteiro de testes finais (`TESTES.md`)

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/dispositivos` | Lista. Parâmetros opcionais: `local`, `status`, `busca`, `ordenar_por`, `direcao` |
| GET | `/locais` | Locais distintos cadastrados (alimenta o filtro) |
| POST | `/dispositivos` | Cadastra (`nome`, `local`) |
| DELETE | `/dispositivos/{id}` | Remove |
| POST | `/dispositivos/{id}/heartbeat` | Marca o dispositivo como online e atualiza a última sincronização |
| POST | `/login` | Recebe `usuario` e `senha` e devolve um token (única rota sem login) |
| POST | `/logout` | Encerra o login atual |
| GET | `/dashboard/resumo` | Métricas gerais: total, online, offline e percentual online |
| GET | `/relatorio/csv` | Exporta os dispositivos em CSV (aceita os mesmos filtros de `GET /dispositivos`) |

Todas as rotas, exceto `POST /login`, exigem o cabeçalho `Authorization: Bearer <token>`.

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
├── BOARD.md              # lista de funcionalidades por sprint (AC1–Final)
├── TESTES.md             # roteiro de testes finais
└── docs/                 # diagrama de classes e diagrama de casos de uso (PNG e SVG)
```

## Próximos passos (ideias futuras)

- Um agente real nos players chamando o heartbeat de tempos em tempos (hoje o botão simula isso).
- Usuários e senhas guardados no banco (hoje há um único usuário configurável).
- Migração do SQLite para SQL Server, sem reescrever a lógica de acesso a dados.
