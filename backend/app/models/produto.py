from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint

from app.database.connection import Base


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)

    codigo = Column(
        String(100),
        nullable=False,
        index=True,
    )

    descricao = Column(
        String(255),
        nullable=False,
    )

    quantidade_caixa = Column(
        Integer,
        nullable=True,
    )

    ativo = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    versao = Column(
        Integer,
        nullable=False,
        default=1,
    )

    atualizado_em = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "codigo",
            name="uq_produtos_codigo",
        ),
    )