from sqlalchemy import Column, Integer, String, Enum, Text
from app.database.connection import Base
from app.enums.conferencia_enums import (
    TipoJustificativa,
    TipoDivergencia
)


class Divergencia(Base):
    __tablename__ = "divergencias"

    id = Column(Integer, primary_key=True, index=True)

    conferencia_id = Column(Integer)
    codigo = Column(String)

    xml = Column(Integer)
    contado = Column(Integer)
    diferenca = Column(Integer)

    tipo = Column(Enum(TipoDivergencia))

    origem = Column(
        String,
        default="NOTA"
    )

    # Versão da conferência em que a divergência foi gerada
    versao = Column(
        Integer,
        nullable=False,
        default=1
    )

    # A divergência nasce sem justificativa.
    # A justificativa passa a ser obrigatória para finalizar.
    justificativa_tipo = Column(
        Enum(TipoJustificativa),
        nullable=True
    )

    justificativa_descricao = Column(
        Text,
        nullable=True
    )