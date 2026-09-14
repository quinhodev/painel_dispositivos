"""
Configuração da conexão com o banco de dados.

Este arquivo não define NENHUMA tabela — ele só monta a "ponte" entre
o código Python e o arquivo físico do banco (SQLite). As tabelas em si
ficam em models.py.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# URL de conexão. "sqlite:///./dispositivos.db" significa: use o SQLite,
# e o arquivo do banco fica na mesma pasta onde o servidor é executado.
# Se um dia quiser migrar para SQL Server, é só trocar essa URL
# (ex: "mssql+pyodbc://usuario:senha@servidor/banco") — o resto do
# código (models, schemas, rotas) não precisa mudar, porque o SQLAlchemy
# abstrai as diferenças entre bancos.
SQLALCHEMY_DATABASE_URL = "sqlite:///./dispositivos.db"

# O "engine" é o objeto que sabe como falar com o banco de fato.
# connect_args é uma particularidade do SQLite: por padrão ele não deixa
# a mesma conexão ser usada por threads diferentes, mas o FastAPI pode
# atender requisições em threads diferentes — por isso liberamos aqui.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal é uma "fábrica" de sessões. Cada requisição HTTP que
# chega na API vai abrir a sua própria sessão a partir daqui.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base é a classe da qual todo modelo de tabela (ex: Dispositivo, em
# models.py) precisa herdar, para o SQLAlchemy saber que aquela classe
# representa uma tabela do banco.
Base = declarative_base()


def get_db():
    """
    Função de dependência usada pelo FastAPI (via Depends(get_db) nas rotas).

    Abre uma sessão nova, entrega ela para a rota que está sendo executada
    (o "yield" pausa aqui até a rota terminar) e garante, no "finally",
    que a conexão é fechada no final — mesmo se a rota der erro no meio
    do caminho. Isso evita conexões "penduradas" no banco.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
