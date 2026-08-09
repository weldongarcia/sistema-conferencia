from app.models.contagem import Contagem
from app.models.conferencia import Conferencia
from app.models.item_nf import ItemNF
from fastapi import HTTPException
from app.models.contagem_historico import ContagemHistorico
from app.enums.conferencia_enums import StatusItem
from app.core.status import ITEM_OK, ITEM_DIVERGENTE, ITEM_NAO_CONFERIDO


def reduzir_codigo_barras(codigo_barras: str) -> str:
    codigo_barras = codigo_barras.strip()

    if not codigo_barras.isdigit():
        raise HTTPException(
            400,
            "Código de barras inválido"
        )

    if len(codigo_barras) != 13:
        raise HTTPException(
            400,
            "O código de barras deve possuir 13 dígitos"
        )

    return codigo_barras[7:12]


def criar_contagem(db, dados, usuario):

    codigo = reduzir_codigo_barras(dados.codigo)

    conferencia = db.query(Conferencia).filter_by(
        id=dados.conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(404, "Conferência não encontrada")

    if conferencia.status == "FINALIZADA":
        raise HTTPException(400, "Conferência finalizada")

    item_existe = db.query(ItemNF).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=codigo
    ).first()

    if not item_existe:
        raise HTTPException(400, "Produto não existe na NF")

    contagem_existente = db.query(Contagem).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=codigo
    ).first()

    # UPDATE
    if contagem_existente:

        if contagem_existente.quantidade == dados.quantidade:
            return contagem_existente

        historico = ContagemHistorico(
            conferencia_id=dados.conferencia_id,
            codigo=codigo,
            valor_anterior=contagem_existente.quantidade,
            valor_novo=dados.quantidade,
            versao=conferencia.versao,
            usuario_id=usuario.id,
        )

        db.add(historico)

        contagem_existente.quantidade = dados.quantidade

        db.commit()
        db.refresh(contagem_existente)

        return contagem_existente

    # INSERT
    contagem = Contagem(
        conferencia_id=dados.conferencia_id,
        codigo=codigo,
        quantidade=dados.quantidade
    )

    db.add(contagem)

    historico = ContagemHistorico(
        conferencia_id=dados.conferencia_id,
        codigo=codigo,
        valor_anterior=0,
        valor_novo=dados.quantidade,
        versao=conferencia.versao,
        usuario_id=usuario.id
    )

    db.add(historico)

    db.commit()
    db.refresh(contagem)

    return contagem