from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database.connection import Base
from sqlalchemy.orm import relationship


class ContagemHistorico(Base):
    __tablename__ = 'contagens_historico'

    id = Column(Integer, primary_key=True, index=True)

    conferencia_id = Column(Integer)
    codigo = Column(String)

    valor_anterior = Column(Integer)
    valor_novo = Column(Integer)

    versao = Column(Integer)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id")
        
        )
    usuario = relationship("Usuario")

    data_alteracao = Column(DateTime, default=datetime.utcnow)

    