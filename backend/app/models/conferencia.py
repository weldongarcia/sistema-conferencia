from sqlalchemy import Column, Integer, DateTime, Enum
from datetime import datetime

from app.database.connection import Base
from app.enums.conferencia_enums import StatusConferencia


class Conferencia(Base):
    __tablename__ = "conferencias"

    id = Column(Integer, primary_key=True, index=True)

    estabelecimento_id = Column(Integer)
    usuario_id = Column(Integer)

    quantidade_reaberturas = Column(Integer, default=0)
    versao = Column(Integer, default=1)

    status = Column(
        Enum(StatusConferencia),
        default=StatusConferencia.RASCUNHO
    )

    data_inicio = Column(
        DateTime,
          default=datetime.utcnow
    )