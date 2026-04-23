from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database.connection import Base


class ContagemHistorico(Base):
    __tablename__ = 'contagens_historico'
    id = Column(Integer, primary_key=True, index=True)
    conferencia_id = Column(Integer)
    codigo = Column(String)
    valor_anterior = Column(Integer)
    valor_novo = Column(Integer)
    data_alteracao = Column(DateTime, default=datetime.utcnow)
    usuario = Column(String)
    