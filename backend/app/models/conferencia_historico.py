from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime
from app.database.connection import Base
from sqlalchemy.orm import relationship

class ConferenciaHistorico(Base):
    __tablename__ = 'conferencia_historico'

    id = Column(Integer, primary_key=True, index=True)

    conferencia_id = Column(Integer, nullable=False)
    usuario_id = Column(
        Integer, 
        ForeignKey("usuario.id"),
        nullable=False
        
    )
    usuario = relationship("Usuario")

    acao = Column(String, nullable=False)

    versao = Column(Integer, nullable=False)

    motivo = Column(Text, nullable=True)

    data_evento = Column(
        DateTime,
        default=datetime.utcnow
    )
    