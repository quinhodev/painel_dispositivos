"""
Ponto de entrada da API (rotas HTTP) — versão FINAL.

Este arquivo só ORQUESTRA: recebe a requisição, valida com schemas.py,
manda os models.py conversarem com o banco via database.py, e devolve
a resposta. A regra é: nenhuma lógica de banco "crua" deveria morar
aqui sem passar pelas camadas de baixo.

Escopo acumulado:
- AC1: cadastrar, listar e remover dispositivos.
- AC2: filtro por local e por status, busca por nome e ordenação.
- AC3: heartbeat (o dispositivo avisa que está ativo) e marcação automática
  como offline quando fica tempo demais sem avisar.
- FINAL: autenticação simples (login com token), dashboard com métricas gerais
  e exportação de relatório em CSV.
"""

import csv
import datetime
import io
import os
import secrets
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
import schemas
from database import engine, get_db

# Cria as tabelas no banco (se ainda não existirem) assim que o servidor sobe.
# Equivale a rodar "CREATE TABLE IF NOT EXISTS ..." pra cada classe de models.py.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Painel de Gestão de Dispositivos")

# CORS = Cross-Origin Resource Sharing. Por padrão, o navegador bloqueia
# uma página (ex: aberta como arquivo local ou em outra porta) de fazer
# requisições para uma API em outro endereço, por segurança.
# Como o front-end (frontend/index.html) e o back-end (localhost:8000)
# são "origens" diferentes do ponto de vista do navegador, precisamos
# liberar isso explicitamente. allow_origins=["*"] libera geral — ok
# para um projeto acadêmico local, mas em produção o ideal seria
# restringir para o domínio real do front-end.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# AC3: tempo máximo (em minutos) que um dispositivo pode ficar sem enviar
# heartbeat antes de ser marcado como offline. Em um sistema real seria
# maior (vários minutos); está curto para dar pra mostrar no vídeo.
TEMPO_LIMITE_MINUTOS = 1


def agora_utc() -> datetime.datetime:
    """
    AC3: data/hora atual em UTC, sem informação de fuso.

    O models.py grava ultima_sincronizacao em UTC sem fuso (datetime.utcnow),
    então usamos o mesmo formato aqui para poder comparar as duas datas.
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def marcar_offline_expirados(db: Session):
    """
    AC3: marca como "offline" os dispositivos online que estão sem heartbeat
    há mais de TEMPO_LIMITE_MINUTOS.

    Em vez de rodar um processo em segundo plano, essa checagem acontece
    sempre que alguém pede a lista. Assim o status mostrado (e os filtros
    por status) nunca ficam desatualizados.
    """
    limite = agora_utc() - datetime.timedelta(minutes=TEMPO_LIMITE_MINUTOS)
    db.query(models.Dispositivo).filter(
        models.Dispositivo.status == "online",
        models.Dispositivo.ultima_sincronizacao < limite,
    ).update({"status": "offline"}, synchronize_session=False)
    db.commit()


# ============================================================
# ENTREGA FINAL: AUTENTICAÇÃO SIMPLES
# ============================================================

# Usuário e senha do painel. Podem ser trocados por variáveis de ambiente
# (PAINEL_USUARIO e PAINEL_SENHA) sem mexer no código; se não existirem,
# valem os padrões abaixo (suficientes para um projeto acadêmico local).
USUARIO_ADMIN = os.environ.get("PAINEL_USUARIO", "admin")
SENHA_ADMIN = os.environ.get("PAINEL_SENHA", "admin123")

# Por quanto tempo um login continua valendo.
TOKEN_VALIDADE_HORAS = 8

# Logins ativos: {token: data/hora em que expira}. Fica só na memória do
# servidor, então reiniciar o uvicorn derruba todos os logins (é esperado).
TOKENS: dict[str, datetime.datetime] = {}

# O HTTPBearer lê o cabeçalho "Authorization: Bearer <token>" e também faz
# aparecer o botão "Authorize" no Swagger (/docs). Usamos auto_error=False
# porque a mensagem de erro (401) é montada na função exigir_login.
esquema_bearer = HTTPBearer(auto_error=False)


def exigir_login(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer)) -> str:
    """
    Dependência que protege as rotas: só deixa passar quem enviou um token
    válido no cabeçalho Authorization. Caso contrário, responde 401
    ("não autenticado") e a rota nem chega a ser executada.

    Devolve o próprio token (a rota de logout usa isso para encerrá-lo).
    """
    if credenciais is None:
        raise HTTPException(
            status_code=401,
            detail="Login necessário",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credenciais.credentials
    expira_em = TOKENS.get(token)
    if expira_em is None or expira_em < agora_utc():
        TOKENS.pop(token, None)  # limpa o token vencido, se existir
        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou expirada",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# AC2: colunas que o front-end pode pedir para ordenar a lista.
# Usamos uma lista fixa (em vez de aceitar qualquer texto vindo da URL)
# para que o usuário só consiga ordenar por colunas que realmente existem.
# (O tipo dict[str, Any] só evita avisos do editor com os tipos do SQLAlchemy.)
COLUNAS_ORDENAVEIS: dict[str, Any] = {
    "id": models.Dispositivo.id,
    "nome": models.Dispositivo.nome,
    "local": models.Dispositivo.local,
    "status": models.Dispositivo.status,
    "ultima_sincronizacao": models.Dispositivo.ultima_sincronizacao,
}


def consultar_dispositivos(
    db: Session,
    local: str | None,
    status: str | None,
    busca: str | None,
    ordenar_por: str,
    direcao: str,
):
    """
    FINAL: monta e executa a consulta de dispositivos com filtros e ordenação.

    Foi separada da rota para ser reaproveitada: tanto a listagem
    (GET /dispositivos) quanto a exportação CSV (GET /relatorio/csv) usam
    exatamente a mesma consulta, então o relatório sempre bate com a tela.
    """
    # AC3: atualiza os status vencidos antes de consultar.
    marcar_offline_expirados(db)

    # Montamos a consulta em partes: começa pegando tudo e vamos
    # acrescentando um .filter() para cada filtro que veio preenchido.
    query = db.query(models.Dispositivo)

    if local:
        query = query.filter(models.Dispositivo.local == local)
    if status:
        query = query.filter(models.Dispositivo.status == status)
    if busca:
        # ilike = LIKE sem diferenciar maiúscula de minúscula; os "%" são
        # curingas de "qualquer coisa antes/depois" (busca por trecho do nome).
        query = query.filter(models.Dispositivo.nome.ilike(f"%{busca}%"))

    # Se vier uma coluna desconhecida, cai no "id" (ordem de cadastro).
    coluna = COLUNAS_ORDENAVEIS.get(ordenar_por, COLUNAS_ORDENAVEIS["id"])
    query = query.order_by(coluna.desc() if direcao == "desc" else coluna.asc())

    return query.all()


@app.get("/dispositivos", response_model=list[schemas.Dispositivo], dependencies=[Depends(exigir_login)])
def listar_dispositivos(
    local: str | None = None,       # AC2: filtra pelo local exato
    status: str | None = None,      # AC2: filtra por "online" ou "offline"
    busca: str | None = None,       # AC2: texto que o nome precisa conter
    ordenar_por: str = "id",        # AC2: coluna usada na ordenação
    direcao: str = "asc",           # AC2: "asc" (crescente) ou "desc" (decrescente)
    db: Session = Depends(get_db),
):
    """
    AC1: lista os dispositivos cadastrados.
    AC2: aceita filtros e ordenação opcionais, passados na URL (query params).
    Ex: /dispositivos?local=Loja Centro&busca=totem&ordenar_por=nome
    AC3: antes de listar, marca como offline quem está sem heartbeat há muito tempo.
    FINAL: exige login (token no cabeçalho Authorization).

    Todos os parâmetros são opcionais: sem nenhum deles, o comportamento é
    o mesmo da AC1 (lista tudo). Quando vários filtros vêm juntos, eles se
    combinam com "E" (o dispositivo precisa atender a todos).
    """
    return consultar_dispositivos(db, local, status, busca, ordenar_por, direcao)


@app.get("/locais", response_model=list[str], dependencies=[Depends(exigir_login)])
def listar_locais(db: Session = Depends(get_db)):
    """
    AC2: devolve os locais distintos já cadastrados (sem repetir).

    Alimenta o <select> de filtro do front-end. Fica em uma rota separada
    de propósito: se o select fosse montado com a lista já filtrada, ele
    perderia as outras opções assim que o usuário escolhesse um local.
    """
    linhas = db.query(models.Dispositivo.local).distinct().order_by(models.Dispositivo.local).all()
    return [linha[0] for linha in linhas]


@app.post("/dispositivos", response_model=schemas.Dispositivo, dependencies=[Depends(exigir_login)])
def criar_dispositivo(dispositivo: schemas.DispositivoCreate, db: Session = Depends(get_db)):
    """
    AC1: cadastra um novo dispositivo.

    O parâmetro `dispositivo` já chega validado pelo FastAPI: se o JSON
    enviado não tiver "nome" e "local", a requisição é rejeitada com
    erro 422 antes mesmo de entrar nesta função.
    """
    novo = models.Dispositivo(**dispositivo.model_dump())
    db.add(novo)      # marca o objeto para ser inserido (ainda não grava)
    db.commit()       # executa o INSERT de fato e salva no arquivo do banco
    db.refresh(novo)  # busca de volta o objeto já com id e ultima_sincronizacao gerados
    return novo


@app.delete("/dispositivos/{dispositivo_id}", dependencies=[Depends(exigir_login)])
def remover_dispositivo(dispositivo_id: int, db: Session = Depends(get_db)):
    """AC1: remove um dispositivo pelo id."""
    dispositivo = db.query(models.Dispositivo).filter(models.Dispositivo.id == dispositivo_id).first()
    if not dispositivo:
        # 404 = "não encontrado". Sem essa checagem, tentar remover um
        # id inexistente falharia de forma confusa mais adiante.
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    db.delete(dispositivo)
    db.commit()
    return {"ok": True}


@app.post("/dispositivos/{dispositivo_id}/heartbeat", response_model=schemas.Dispositivo, dependencies=[Depends(exigir_login)])
def heartbeat(dispositivo_id: int, db: Session = Depends(get_db)):
    """
    AC3: o dispositivo avisa que está ativo ("heartbeat" = batimento cardíaco).

    Em um sistema real, o próprio player de sinalização chamaria esta rota
    de tempos em tempos. Aqui, o botão "Heartbeat" da tela simula isso.
    A cada chamada o dispositivo passa para "online" e a data da última
    sincronização é atualizada para o momento atual.
    """
    dispositivo = db.query(models.Dispositivo).filter(models.Dispositivo.id == dispositivo_id).first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    db.query(models.Dispositivo).filter(models.Dispositivo.id == dispositivo_id).update(
        {"status": "online", "ultima_sincronizacao": agora_utc()}
    )
    db.commit()
    db.refresh(dispositivo)  # recarrega o objeto já com os valores novos
    return dispositivo


# ============================================================
# ENTREGA FINAL: LOGIN, DASHBOARD E EXPORTAÇÃO
# ============================================================

@app.post("/login", response_model=schemas.TokenResposta)
def login(dados: schemas.LoginEntrada):
    """
    FINAL: confere usuário e senha e, se estiverem certos, devolve um token.

    É a única rota que NÃO exige login. O front-end guarda o token e o envia
    em todas as chamadas seguintes (cabeçalho "Authorization: Bearer <token>").
    """
    # compare_digest compara em tempo constante (não dá para descobrir a senha
    # pelo tempo de resposta) e exige bytes para aceitar caracteres acentuados.
    usuario_ok = secrets.compare_digest(dados.usuario.encode("utf-8"), USUARIO_ADMIN.encode("utf-8"))
    senha_ok = secrets.compare_digest(dados.senha.encode("utf-8"), SENHA_ADMIN.encode("utf-8"))
    if not (usuario_ok and senha_ok):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    token = secrets.token_urlsafe(32)  # texto aleatório e imprevisível
    TOKENS[token] = agora_utc() + datetime.timedelta(hours=TOKEN_VALIDADE_HORAS)
    return {"token": token}


@app.post("/logout")
def logout(token: str = Depends(exigir_login)):
    """FINAL: encerra o login atual (o token deixa de valer)."""
    TOKENS.pop(token, None)
    return {"ok": True}


@app.get("/dashboard/resumo", response_model=schemas.ResumoDashboard, dependencies=[Depends(exigir_login)])
def resumo_dashboard(db: Session = Depends(get_db)):
    """
    FINAL: métricas gerais para o topo da tela: total de dispositivos,
    quantos estão online/offline e o percentual online.
    """
    # Atualiza os status vencidos antes de contar, para os números baterem com a lista.
    marcar_offline_expirados(db)

    total = db.query(models.Dispositivo).count()
    online = db.query(models.Dispositivo).filter(models.Dispositivo.status == "online").count()
    offline = total - online
    percentual_online = round(online / total * 100, 1) if total else 0.0

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "percentual_online": percentual_online,
    }


def proteger_csv(valor: Any) -> str:
    """
    Planilhas (Excel, Sheets) tratam texto que começa com = + - ou @ como
    fórmula. Para um nome malicioso não virar fórmula no relatório, colocamos
    um apóstrofo na frente.
    """
    texto = str(valor)
    if texto and texto[0] in "=+-@":
        return "'" + texto
    return texto


def formatar_data(data: Any) -> str:
    """Formata a data para o relatório (continua em UTC, como está no banco)."""
    return data.strftime("%d/%m/%Y %H:%M:%S")


@app.get("/relatorio/csv", dependencies=[Depends(exigir_login)])
def exportar_csv(
    local: str | None = None,
    status: str | None = None,
    busca: str | None = None,
    ordenar_por: str = "id",
    direcao: str = "asc",
    db: Session = Depends(get_db),
):
    """
    FINAL: exporta os dispositivos em CSV, respeitando os mesmos filtros e a
    mesma ordenação da listagem (o relatório é o que está na tela).
    """
    dispositivos: list[Any] = consultar_dispositivos(db, local, status, busca, ordenar_por, direcao)

    saida = io.StringIO()
    # Ponto e vírgula como separador: é o que o Excel em português espera.
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["ID", "Nome", "Local", "Status", "Última sincronização (UTC)"])
    for d in dispositivos:
        escritor.writerow([
            d.id,
            proteger_csv(d.nome),
            proteger_csv(d.local),
            d.status,
            formatar_data(d.ultima_sincronizacao),
        ])

    # "\ufeff" (BOM) no começo faz o Excel reconhecer o UTF-8 e mostrar os acentos certos.
    conteudo = "\ufeff" + saida.getvalue()
    return Response(
        content=conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dispositivos.csv"'},
    )
