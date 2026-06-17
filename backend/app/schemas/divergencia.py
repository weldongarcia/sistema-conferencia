from pydantic import BaseModel

class JustificarDivergencia(BaseModel):
    justificativa_tipo: str
    justificativa_descricao: str