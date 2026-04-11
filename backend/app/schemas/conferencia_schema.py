from pydantic import BaseModel
from datetime import datetime

class ConferenciaCreate(BaseModel):
    estabelecimento_id: int
    usuario_id: int

class ConferenciaResponse(BaseModel):
    id: int
    estabelecimento_id: int
    usuario_id: int
    status: str
    data_inicio: datetime

    class Config:
        from_attributes = True  # substitui orm_mode no FastAPI novo