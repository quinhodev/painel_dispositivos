"""
Ponto de entrada da API (rotas HTTP) — versão AC2.

Este arquivo só ORQUESTRA: recebe a requisição, valida com schemas.py,
manda os models.py conversarem com o banco via database.py, e devolve
a resposta. A regra é: nenhuma lógica de banco "crua" deveria morar
aqui sem passar pelas camadas de baixo.

Escopo acumulado:
- AC1: cadastrar, listar e remover dispositivos.
- AC2: filtro por local e por status, busca por nome e ordenação.
Heartbeat e dashboard entram nas próximas entregas.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Any
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


# AC2: colunas que o front-end pode pedir para ordenar a lista.
# Usamos uma lista fixa (em vez de aceitar qualquer texto vindo da URL)
# para que o usuário só consiga ordenar por colunas que realmente existem.
COLUNAS_ORDENAVEIS: dict[str, Any] = {
    "id": models.Dispositivo.id,
    "nome": models.Dispositivo.nome,
    "local": models.Dispositivo.local,
    "status": models.Dispositivo.status,
    "ultima_sincronizacao": models.Dispositivo.ultima_sincronizacao,
}


@app.get("/dispositivos", response_model=list[schemas.Dispositivo])
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

    Todos os parâmetros são opcionais: sem nenhum deles, o comportamento é
    o mesmo da AC1 (lista tudo). Quando vários filtros vêm juntos, eles se
    combinam com "E" (o dispositivo precisa atender a todos).
    """
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


@app.get("/locais", response_model=list[str])
def listar_locais(db: Session = Depends(get_db)):
    """
    AC2: devolve os locais distintos já cadastrados (sem repetir).

    Alimenta o <select> de filtro do front-end. Fica em uma rota separada
    de propósito: se o select fosse montado com a lista já filtrada, ele
    perderia as outras opções assim que o usuário escolhesse um local.
    """
    linhas = db.query(models.Dispositivo.local).distinct().order_by(models.Dispositivo.local).all()
    return [linha[0] for linha in linhas]


@app.post("/dispositivos", response_model=schemas.Dispositivo)
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


@app.delete("/dispositivos/{dispositivo_id}")
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
