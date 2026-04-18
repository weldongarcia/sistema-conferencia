from sqlalchemy.orm import Session
from app.models.item_nf import ItemNF
from app.models.contagem import Contagem
from collections import defaultdict
from app.models.divergencia import Divergencia
from app.models.conferencia import Conferencia
from fastapi import HTTPException


def comparar_conferencia(db: Session, conferencia_id: int):

    itens_nf = db.query(ItemNF).filter_by(conferencia_id=conferencia_id).all()
    contagens = db.query(Contagem).filter_by(conferencia_id=conferencia_id).all()

    mapa_xml = defaultdict(float)
    for item in itens_nf:
        mapa_xml[item.codigo] += float(item.quantidade)

    mapa_contagem = defaultdict(float)
    for c in contagens:
        mapa_contagem[c.codigo] += c.quantidade

    resultado = []

    codigos = set(mapa_xml.keys()) | set(mapa_contagem.keys())

    # limpar divergencias antigas
    db.query(Divergencia).filter_by(conferencia_id=conferencia_id).delete()

    for codigo in codigos:
        xml_qtd = mapa_xml.get(codigo, 0)
        cont_qtd = mapa_contagem.get(codigo, 0)

        diferenca = cont_qtd - xml_qtd

        resultado.append({
            "codigo": codigo,
            "xml": xml_qtd,
            "contado": cont_qtd,
            "diferenca": diferenca
        })

        if diferenca != 0:
            db.add(Divergencia(
                conferencia_id=conferencia_id,
                codigo=codigo,
                xml=xml_qtd,
                contado=cont_qtd,
                diferenca=diferenca
            ))

    db.commit()

    total_itens = len(resultado)
    divergentes = sum(1 for item in resultado if item["diferenca"] != 0)

    return {
        "status": "divergente" if divergentes > 0 else "ok",
        "total_itens": total_itens,
        "divergentes": divergentes,
        "itens": resultado
    }


def criar_contagem(db, dados):

    conferencia = db.query(Conferencia).filter_by(id=dados.conferencia_id).first()

    if not conferencia:
        raise HTTPException(404, "Conferência não encontrada")

    if conferencia.status == "finalizado":
        raise HTTPException(400, "Conferência finalizada. Não pode alterar.")

    item_existe = db.query(ItemNF).filter_by(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo
    ).first()

    if not item_existe:
        raise HTTPException(400, "Produto não existe no XML dessa conferência")

    contagem = Contagem(
        conferencia_id=dados.conferencia_id,
        codigo=dados.codigo,
        quantidade=dados.quantidade
    )

    db.add(contagem)
    db.commit()
    db.refresh(contagem)

    return contagem


def fechar_conferencia(db: Session, conferencia_id: int):

    conferencia = db.query(Conferencia).filter_by(id=conferencia_id).first()

    if not conferencia:
        raise HTTPException(404, 'Conferência não encontrada')
    
    if conferencia.status == 'finalizado':
        return {'msg': 'Conferência já está finalizada'}
    
    # nova regra:

    divergencias = db.query(Divergencia).filter_by(
        conferencia_id=conferencia_id
    ).count()

    if divergencias > 0:
        raise HTTPException(
            400,
            "Existem divergências. Conferência não pode ser finalizada."
        )

    conferencia.status = "finalizado"

    db.commit()

    return {"msg": "Conferência finalizada com sucesso"}