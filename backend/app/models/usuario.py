from sqlalchemy import Column, Integer, String

from app.database.connection import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String,
        unique=True,
        nullable=False
    )

    senha = Column(
        String,
        nullable=False
    )

    perfil = Column(
        String,
        nullable=False
    )

    estabelecimento_id = Column(
        Integer,
        nullable=True,
        index=True
    )