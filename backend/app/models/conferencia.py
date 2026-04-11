from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database.connection import Base

class Conferencia(Base):
    __tablename__ = "conferencias"

    id = Column(Integer, primary_key=True, index=True)
    estabelecimento_id = Column(Integer)
    usuario_id = Column(Integer)
    status = Column(String, default="aberto")
    data_inicio = Column(DateTime, default=datetime.utcnow)