from pydantic import BaseModel


class ItemSincronizacao(BaseModel):
    codigo: str
    quantidade: int


class SincronizacaoContagem(BaseModel):
    itens: list[ItemSincronizacao]