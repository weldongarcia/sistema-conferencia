from pydantic import BaseModel

from app.enums.conferencia_enums import TipoJustificativa


class JustificarDivergencia(BaseModel):
    justificativa_tipo: TipoJustificativa
    justificativa_descricao: str