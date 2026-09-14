"""
Ponto de entrada da API (rotas HTTP) — versão AC1.

Este arquivo só ORQUESTRA: recebe a requisição, valida com schemas.py,
manda os models.py conversarem com o banco via database.py, e devolve
a resposta. A regra é: nenhuma lógica de banco "crua" deveria morar
aqui sem passar pelas camadas de baixo.

Escopo desta entrega (AC1): cadastrar, listar e remover dispositivos.
Filtros, heartbeat e dashboard entram nas próximas entregas.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/dispositivos", response_model=list[schemas.Dispositivo])
def listar_dispositivos(db: Session = Depends(get_db)):
    """AC1: lista todos os dispositivos cadastrados."""
    return db.query(models.Dispositivo).all()


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
