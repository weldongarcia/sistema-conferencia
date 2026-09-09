from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.schemas.produto import ProdutoAtualizacao, ProdutoCriacao, ProdutoResposta, ProdutoSincronizacao
from app.services.produtos_service import atualizar_produto, criar_produto, desativar_produto, listar_produtos, obter_produto, sincronizar_produtos
from app.utils.auth import get_current_user
from app.core.perfis import AUDITOR, CONFERENTE
from app.core.security import exigir_perfil

router = APIRouter(prefix="/produtos", tags=["Produtos"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/sincronizar/{versao_local}", response_model=ProdutoSincronizacao)
def sincronizar(versao_local: int, offset: int = Query(0, ge=0),
                limite: int = Query(500, ge=1, le=1000),
                db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    exigir_perfil(usuario, [CONFERENTE])
    return sincronizar_produtos(db, versao_local, offset, limite)

@router.get("/", response_model=list[ProdutoResposta])
def listar(apenas_ativos: bool = True, db: Session = Depends(get_db),
           usuario=Depends(get_current_user)):
    exigir_perfil(usuario, [AUDITOR, CONFERENTE])
    return listar_produtos(db, apenas_ativos)

@router.get("/{produto_id}", response_model=ProdutoResposta)
def buscar(produto_id: int, db: Session = Depends(get_db),
           usuario=Depends(get_current_user)):
    exigir_perfil(usuario, [AUDITOR, CONFERENTE])
    return obter_produto(db, produto_id)

@router.post("/", response_model=ProdutoResposta)
def criar(dados: ProdutoCriacao, db: Session = Depends(get_db),
          usuario=Depends(get_current_user)):
    exigir_perfil(usuario, [AUDITOR])
    return criar_produto(db, dados)

@router.put("/{produto_id}", response_model=ProdutoResposta)
def atualizar(produto_id: int, dados: ProdutoAtualizacao, db: Session = Depends(get_db),
              usuario=Depends(get_current_user)):
    exigir_perfil(usuario, [AUDITOR])
    return atualizar_produto(db, produto_id, dados)

@router.delete("/{produto_id}", response_model=ProdutoResposta)
def desativar(produto_id: int, db: Session = Depends(get_db),
              usuario=Depends(get_current_user)):
    exigir_perfil(usuario, [AUDITOR])
    return desativar_produto(db, produto_id)
