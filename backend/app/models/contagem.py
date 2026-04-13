from sqlalchemy import Column, Integer, String
from app.database.connection import Base

class Contagem(Base):
    __tablename__ = "contagens"

    id = Column(Integer, primary_key=True, index=True)
    conferencia_id = Column(Integer)
    codigo = Column(String)
    quantidade = Column(Integer)
    