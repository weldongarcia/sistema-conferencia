from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.produto import Produto
from app.schemas.produto import ProdutoAtualizacao, ProdutoCriacao

def _normalizar_codigo(codigo: str) -> str:
    codigo = codigo.strip()
    if not codigo:
        raise HTTPException(400, "Código do produto não informado.")
    return codigo

def _proxima_versao(db: Session) -> int:
    maior = db.query(Produto.versao).order_by(Produto.versao.desc()).first()
    return (maior[0] if maior and maior[0] is not None else 0) + 1

def listar_produtos(db: Session, apenas_ativos: bool = True):
    query = db.query(Produto)
    if apenas_ativos:
        query = query.filter(Produto.ativo.is_(True))
    return query.order_by(Produto.codigo).all()

def obter_produto(db: Session, produto_id: int):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(404, "Produto não encontrado.")
    return produto

def criar_produto(db: Session, dados: ProdutoCriacao):
    codigo = _normalizar_codigo(dados.codigo)
    if db.query(Produto).filter(Produto.codigo == codigo).first():
        raise HTTPException(409, "Já existe produto com este código.")
    produto = Produto(codigo=codigo, descricao=dados.descricao.strip(),
                      quantidade_caixa=dados.quantidade_caixa, ativo=dados.ativo,
                      versao=_proxima_versao(db), atualizado_em=datetime.utcnow())
    db.add(produto); db.commit(); db.refresh(produto)
    return produto

def atualizar_produto(db: Session, produto_id: int, dados: ProdutoAtualizacao):
    produto = obter_produto(db, produto_id)
    if dados.codigo is not None:
        codigo = _normalizar_codigo(dados.codigo)
        conflito = db.query(Produto).filter(Produto.codigo == codigo, Produto.id != produto_id).first()
        if conflito:
            raise HTTPException(409, "Já existe outro produto com este código.")
        produto.codigo = codigo
    if dados.descricao is not None:
        produto.descricao = dados.descricao.strip()
    if dados.quantidade_caixa is not None:
        produto.quantidade_caixa = dados.quantidade_caixa
    if dados.ativo is not None:
        produto.ativo = dados.ativo
    produto.versao = _proxima_versao(db)
    produto.atualizado_em = datetime.utcnow()
    db.commit(); db.refresh(produto)
    return produto

def desativar_produto(db: Session, produto_id: int):
    produto = obter_produto(db, produto_id)
    produto.ativo = False
    produto.versao = _proxima_versao(db)
    produto.atualizado_em = datetime.utcnow()
    db.commit(); db.refresh(produto)
    return produto

def sincronizar_produtos(db: Session, versao_local: int, offset: int = 0, limite: int = 500):
    if versao_local < 0:
        raise HTTPException(400, "Versão local inválida.")
    if offset < 0:
        raise HTTPException(400, "Offset inválido.")
    if limite < 1 or limite > 1000:
        raise HTTPException(400, "O limite deve estar entre 1 e 1000.")

    query = db.query(Produto).filter(Produto.versao > versao_local)
    total = query.count()
    produtos = (query.order_by(Produto.versao, Produto.id)
                     .offset(offset).limit(limite).all())
    maior = db.query(Produto.versao).order_by(Produto.versao.desc()).first()
    versao_atual = maior[0] if maior and maior[0] is not None else versao_local
    return {"versao": versao_atual, "offset": offset, "limite": limite,
            "total": total, "tem_mais": offset + len(produtos) < total,
            "produtos": produtos}
