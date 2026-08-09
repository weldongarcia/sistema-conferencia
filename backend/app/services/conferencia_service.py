from sqlalchemy.orm import Session
from app.models.item_nf import ItemNF
from app.models.contagem import Contagem
from collections import defaultdict
from app.models.divergencia import Divergencia
from app.models.conferencia import Conferencia
from fastapi import HTTPException
from app.enums.conferencia_enums import TipoDivergencia
from app.enums.conferencia_enums import StatusConferencia
from app.core.status import STATUS_FINALIZADA, STATUS_REABERTA, STATUS_REPROVADA, STATUS_ABERTA, STATUS_APROVADA
from app.services.conferencia_historico_service import registrar_historico
from app.utils.codigo import normalizar_codigo

def comparar_conferencia(db: Session, conferencia_id: int):

    itens_nf = db.query(ItemNF).filter_by(
        conferencia_id=conferencia_id
    ).all()

    contagens = db.query(Contagem).filter_by(
        conferencia_id=conferencia_id
    ).all()

    mapa_xml = defaultdict(float)

    for item in itens_nf:
        codigo = normalizar_codigo(item.codigo)

        mapa_xml[codigo] += float(item.quantidade)

    mapa_contagem = defaultdict(float)

    for c in contagens:
        codigo = normalizar_codigo(c.codigo)

        mapa_contagem[codigo] += c.quantidade

    resultado = []

    codigos = set(mapa_xml.keys()) | set(mapa_contagem.keys())

    # Limpar divergências antigas
    db.query(Divergencia).filter_by(
        conferencia_id=conferencia_id
    ).delete()

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

        # Produto que não existe na NF
        if codigo not in mapa_xml:

            tipo = TipoDivergencia.PRODUTO_A_MAIS
            origem = "FORA_NOTA"

        # Produto da NF que não foi contado
        elif codigo not in mapa_contagem:

            tipo = TipoDivergencia.PRODUTO_NAO_ENCONTRADO
            origem = "NOTA"

        # Quantidade contada menor
        elif diferenca < 0:

            tipo = TipoDivergencia.QUANTIDADE_MENOR
            origem = "NOTA"

        # Quantidade contada maior
        elif diferenca > 0:

            tipo = TipoDivergencia.QUANTIDADE_MAIOR
            origem = "NOTA"

        # Sem divergência
        else:
            continue

        db.add(
            Divergencia(
                conferencia_id=conferencia_id,
                codigo=codigo,
                xml=xml_qtd,
                contado=cont_qtd,
                diferenca=diferenca,
                tipo=tipo,
                origem=origem
            )
        )

    db.commit()

    total_itens = len(resultado)

    divergentes = sum(
        1
        for item in resultado
        if item["diferenca"] != 0
    )

    return {
        "status": "divergente" if divergentes > 0 else "ok",
        "total_itens": total_itens,
        "divergentes": divergentes,
        "itens": resultado
    }
    

    if codigo not in mapa_xml:
        tipo = TipoDivergencia.PRODUTO_A_MAIS
        origem = "FORA_NOTA"

    elif codigo not in mapa_contagem:
        tipo = TipoDivergencia.PRODUTO_NAO_ENCONTRADO
        origem = "NOTA"

    elif diferenca < 0:
        tipo = TipoDivergencia.QUANTIDADE_MENOR
        origem = "NOTA"

    else:
        tipo = TipoDivergencia.QUANTIDADE_MAIOR
        origem = "NOTA"

    db.add(Divergencia(
        conferencia_id=conferencia_id,
        codigo=codigo,
        xml=xml_qtd,
        contado=cont_qtd,
        diferenca=diferenca,
        tipo=tipo,
        origem=origem
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


def fechar_conferencia(
        db: Session,
        conferencia_id: int,
        usuario_id: int
):

    conferencia = db.query(Conferencia).filter_by(id=conferencia_id).first()

    if not conferencia:
        raise HTTPException(404, 'Conferência não encontrada')
    
    if conferencia.status == STATUS_FINALIZADA:
        return {'msg': 'Conferência já está finalizada'}
    
    # nova regra:

    divergencias = db.query(Divergencia).filter_by(
        conferencia_id=conferencia_id
    ).count()

    divergencias_sem_justificativa = db.query(Divergencia).filter(
    Divergencia.conferencia_id == conferencia_id,
    Divergencia.justificativa_tipo == None
).count()

    if divergencias_sem_justificativa > 0:
      raise HTTPException(
        400,
        "Existem divergências sem justificativa."
    )

    conferencia.status = StatusConferencia.FINALIZADA

    registrar_historico(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=usuario_id,
        acao="FINALIZADA",
        versao=conferencia.versao
    )

    db.commit()

    return {"msg": "Conferência finalizada com sucesso"}

def reabrir_conferencia(db: Session, conferencia_id: int, usuario_id: int, motivo: str):

    conferencia = db.query(Conferencia).filter_by(id=conferencia_id).first()

    if not conferencia:
        raise HTTPException(404, "Conferência não encontrada")

    if not motivo:
        raise HTTPException(400, "Motivo obrigatório")

    if conferencia.status == STATUS_FINALIZADA:
        raise HTTPException(400, "Só pode reabrir conferência finalizada")

    conferencia.status = StatusConferencia.REABERTA
    conferencia.quantidade_reaberturas += 1

    db.commit()

    return {"msg": "Conferência reaberta com sucesso"}

