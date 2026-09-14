"""
Schemas de validação (Pydantic).

Diferença importante em relação a models.py:
- models.py descreve a TABELA do banco.
- schemas.py descreve o formato dos dados que ENTRAM e SAEM da API
  (o "contrato" com quem está consumindo, como o front-end).

O FastAPI usa essas classes para validar automaticamente o JSON
recebido antes de ele chegar no código da rota, e para formatar
a resposta antes de virar JSON de volta.
"""

from pydantic import BaseModel
from typing import Optional
import datetime


class DispositivoBase(BaseModel):
    """Campos em comum entre criação e leitura de um dispositivo."""
    nome: str
    local: str
    status: Optional[str] = "offline"


class DispositivoCreate(DispositivoBase):
    """
    Formato exigido para CRIAR um dispositivo (POST /dispositivos).
    Herda nome/local/status de DispositivoBase — não precisa de nada a mais,
    porque id e ultima_sincronizacao são gerados pelo banco, não pelo usuário.
    """
    pass


class DispositivoUpdate(BaseModel):
    """
    Formato para ATUALIZAR um dispositivo (PUT /dispositivos/{id}).
    Todos os campos são opcionais, porque uma atualização pode alterar
    só um campo (ex: só o status) sem precisar reenviar tudo.
    """
    nome: Optional[str] = None
    local: Optional[str] = None
    status: Optional[str] = None


class Dispositivo(DispositivoBase):
    """
    Formato de SAÍDA da API — o que é devolvido quando se cria, lista
    ou busca um dispositivo. Inclui os campos gerados pelo banco (id e
    ultima_sincronizacao) que não existem em DispositivoCreate.
    """
    id: int
    ultima_sincronizacao: datetime.datetime

    class Config:
        # Permite converter diretamente um objeto do SQLAlchemy
        # (models.Dispositivo) para este schema, sem precisar montar
        # um dicionário na mão em cada rota.
        from_attributes = True
