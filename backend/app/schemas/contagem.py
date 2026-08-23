from pydantic import BaseModel


class ContagemCreate(BaseModel):

    conferencia_id: int

    codigo: str

    quantidade: int

    incluir_na_conferencia: bool = False