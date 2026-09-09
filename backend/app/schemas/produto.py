from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ProdutoBase(BaseModel):
    codigo: str = Field(min_length=1, max_length=100)
    descricao: str = Field(min_length=1, max_length=255)
    quantidade_caixa: int | None = Field(default=None, ge=1)
    ativo: bool = True

class ProdutoCriacao(ProdutoBase):
    pass

class ProdutoAtualizacao(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=100)
    descricao: str | None = Field(default=None, min_length=1, max_length=255)
    quantidade_caixa: int | None = Field(default=None, ge=1)
    ativo: bool | None = None

class ProdutoResposta(ProdutoBase):
    id: int
    versao: int
    atualizado_em: datetime
    model_config = ConfigDict(from_attributes=True)

class ProdutoSincronizacao(BaseModel):
    versao: int
    offset: int
    limite: int
    total: int
    tem_mais: bool
    produtos: list[ProdutoResposta]
