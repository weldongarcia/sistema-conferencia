from sqlalchemy import Column, Integer, String
from app.database.connection import Base  # ✅ ESSENCIAL

class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id = Column(Integer, primary_key=True, index=True)
    chave_acesso = Column(String, unique=True, index=True)
    numero = Column(String)
    conferencia_id = Column(Integer)