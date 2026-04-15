from sqlalchemy import Column, Integer, String
from app.database.connection import Base

class Divergencia(Base):
    __tablename__ = 'divergencias'

    id = Column(Integer, primary_key=True, index=True)
    conferencia_id = Column(Integer)
    codigo = Column(String)
    xml = Column(Integer)
    contado = Column(Integer)
    diferenca = Column(Integer)
    