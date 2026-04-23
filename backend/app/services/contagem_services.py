from app.models.contagem import Contagem
from app.models.conferencia import Conferencia
from app.models.item_nf import ItemNF
from fastapi import HTTPException
from app.models.contagem_historico import ContagemHistorico


def criar_contagem(db, dados, usuario):

    conferencia = db.query(Conferencia).filter_by(
        id=dados.conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada"
        )

    if conferencia.status == "finalizado":
        raise HTTPException(
            status_code=400,
            detail="Conferência finalizada. Não pode alterar."
        )

    item_existe = db.query(ItemNF).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo
    ).first()

    if not item_existe:
        raise HTTPException(
            status_code=400,
            detail="Produto não existe no XML dessa conferência"
        )

    # procura se já existe contagem
    contagem_existente = db.query(Contagem).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo
    ).first()

    # se existir -> UPDATE
    if contagem_existente:

    # 🚫 se não houve mudança, não faz nada
        if contagem_existente.quantidade == dados.quantidade:
            return contagem_existente

    # 📜 salva histórico
    historico = ContagemHistorico(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo,
        valor_anterior=contagem_existente.quantidade,
        valor_novo=dados.quantidade,
        usuario=usuario
    )

    db.add(historico)

    # 🔄 atualiza valor
    contagem_existente.quantidade = dados.quantidade

    db.commit()

    db.refresh(contagem_existente)

    return contagem_existente

    # se NÃO existir -> INSERT
    contagem = Contagem(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo,
        quantidade=dados.quantidade
    )

    db.add(contagem)
    db.commit()
    db.refresh(contagem)

    return contagem
