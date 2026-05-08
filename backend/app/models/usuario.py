from sqlalchemy import Column, Integer, String
from app.database.connection import Base



class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    senha = Column(String)

    perfil = Column(String)
