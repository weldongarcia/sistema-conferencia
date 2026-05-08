from sqlalchemy import Column, Integer, String, Enum, Text
from app.database.connection import Base
from app.enums.conferencia_enums import TipoJustificativa, TipoDivergencia

class Divergencia(Base):
    __tablename__ = 'divergencias'

    id = Column(Integer, primary_key=True, index=True)

    conferencia_id = Column(Integer)
    codigo = Column(String)

    xml = Column(Integer)
    contado = Column(Integer)
    diferenca = Column(Integer)

    tipo = Column(Enum(TipoDivergencia))

    # 🔥 AGORA SIM dentro da classe
    origem = Column(String, default="NOTA")  # NOTA / FORA_NOTA

    justificativa_tipo = Column(Enum(TipoJustificativa), nullable=False)
    justificativa_descricao = Column(Text, nullable=True)
    