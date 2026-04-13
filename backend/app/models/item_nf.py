from sqlalchemy import Column, Integer, String, ForeignKey
from app.database.connection import Base

class ItemNF(Base):
    __tablename__ = "itens_nf"

    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("notas_fiscais.id"))
    codigo = Column(String)
    descricao = Column(String)
    quantidade = Column(String)