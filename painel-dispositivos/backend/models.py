"""
Modelos de banco de dados (ORM).

Cada classe aqui representa uma TABELA do banco. Cada atributo da
classe vira uma COLUNA. O SQLAlchemy usa essas classes tanto para criar
a tabela (veja models.Base.metadata.create_all() em main.py) quanto
para ler/gravar dados sem precisar escrever SQL na mão.
"""

from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime


class Dispositivo(Base):
    """
    Representa um dispositivo de sinalização digital (player/tela)
    cadastrado no sistema.

    Equivalente, em SQL puro, a algo como:
        CREATE TABLE dispositivos (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            local TEXT NOT NULL,
            status TEXT DEFAULT 'offline',
            ultima_sincronizacao DATETIME
        );
    """

    __tablename__ = "dispositivos"

    # Chave primária: gerada automaticamente pelo banco a cada novo registro.
    id = Column(Integer, primary_key=True, index=True)

    # Nome de exibição do dispositivo (ex: "Totem Entrada").
    nome = Column(String, nullable=False)

    # Local físico onde o dispositivo está instalado (ex: "Loja Centro").
    # Usado nos filtros da AC2.
    local = Column(String, nullable=False)

    # Estado atual do dispositivo. Só assume "online" ou "offline" por
    # convenção do projeto — não há uma restrição de banco (CHECK)
    # impedindo outros valores; a validação de entrada fica em schemas.py.
    status = Column(String, default="offline")

    # Data/hora da última vez que o dispositivo "avisou" que está ativo
    # (ver endpoint de heartbeat em main.py). Atualizada automaticamente
    # ao criar o registro e a cada heartbeat recebido.
    ultima_sincronizacao = Column(DateTime, default=datetime.datetime.utcnow)
