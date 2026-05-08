from app.models.contagem import Contagem
from app.models.conferencia import Conferencia
from app.models.item_nf import ItemNF
from fastapi import HTTPException
from app.models.contagem_historico import ContagemHistorico
from app.enums.conferencia_enums import StatusItem
from app.core.status import ITEM_OK, ITEM_DIVERGENTE, ITEM_NAO_CONFERIDO


def criar_contagem(db, dados, usuario):

    conferencia = db.query(Conferencia).filter_by(
        id=dados.conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(404, "Conferência não encontrada")

    if conferencia.status == "FINALIZADA":
        raise HTTPException(400, "Conferência finalizada")

    item_existe = db.query(ItemNF).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo
    ).first()

    if not item_existe:
        raise HTTPException(400, "Produto não existe na NF")

    contagem_existente = db.query(Contagem).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo
    ).first()

    def atualizar_status_item(item):

     if item.quantidade_contada == item.quantidade_esperada:
       item.status = ITEM_OK
     else:
        item.status = ITEM_DIVERGENTE

    # UPDATE
    if contagem_existente:

        if contagem_existente.quantidade == dados.quantidade:
            return contagem_existente

        historico = ContagemHistorico(
            conferencia_id=dados.conferencia_id,
            codigo=dados.codigo,
            valor_anterior=contagem_existente.quantidade,
            valor_novo=dados.quantidade,
            usuario=usuario
        )

        db.add(historico)

        contagem_existente.quantidade = dados.quantidade

        db.commit()
        db.refresh(contagem_existente)

        return contagem_existente

    # INSERT
    contagem = Contagem(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo,
        quantidade=dados.quantidade
    )

    db.add(contagem)
    db.commit()
    db.refresh(contagem)

    return contagem
