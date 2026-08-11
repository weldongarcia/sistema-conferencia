from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.item_nf import ItemNF
from app.models.contagem import Contagem
from app.models.divergencia import Divergencia
from app.models.conferencia import Conferencia

from app.enums.conferencia_enums import (
    TipoDivergencia,
    StatusConferencia
)

from app.core.status import (
    STATUS_FINALIZADA
)

from app.services.conferencia_historico_service import registrar_historico
from app.utils.codigo import normalizar_codigo


# ==========================================================
# COMPARAR CONFERÊNCIA
# ==========================================================

def comparar_conferencia(
    db: Session,
    conferencia_id: int
):

    # ==========================================
    # BUSCAR CONFERÊNCIA
    # ==========================================

    conferencia = db.query(
        Conferencia
    ).filter_by(
        id=conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(
            404,
            "Conferência não encontrada"
        )

    versao_atual = conferencia.versao

    # ==========================================
    # ITENS DA NF
    # ==========================================

    itens_nf = db.query(
        ItemNF
    ).filter_by(
        conferencia_id=conferencia_id
    ).all()

    # ==========================================
    # CONTAGENS
    # ==========================================

    contagens = db.query(
        Contagem
    ).filter_by(
        conferencia_id=conferencia_id
    ).all()

    # ==========================================
    # MAPA XML
    # ==========================================

    mapa_xml = defaultdict(float)

    for item in itens_nf:

        codigo = normalizar_codigo(
            item.codigo
        )

        mapa_xml[codigo] += float(
            item.quantidade
        )

    # ==========================================
    # MAPA CONTAGEM
    # ==========================================

    mapa_contagem = defaultdict(float)

    for c in contagens:

        codigo = normalizar_codigo(
            c.codigo
        )

        mapa_contagem[codigo] += float(
            c.quantidade
        )

    # ==========================================
    # BUSCAR DIVERGÊNCIAS DA VERSÃO ATUAL
    #
    # As versões anteriores permanecem preservadas.
    # ==========================================

    divergencias_existentes = db.query(
        Divergencia
    ).filter(
        Divergencia.conferencia_id == conferencia_id,
        Divergencia.versao == versao_atual
    ).all()

    mapa_divergencias = {
        normalizar_codigo(d.codigo): d
        for d in divergencias_existentes
    }

    # ==========================================
    # RESULTADO
    # ==========================================

    resultado = []

    codigos = (
        set(mapa_xml.keys())
        | set(mapa_contagem.keys())
    )

    # ==========================================
    # COMPARAÇÃO
    # ==========================================

    for codigo in codigos:

        xml_qtd = mapa_xml.get(
            codigo,
            0
        )

        cont_qtd = mapa_contagem.get(
            codigo,
            0
        )

        diferenca = cont_qtd - xml_qtd

        # ======================================
        # DETERMINAR DIVERGÊNCIA
        # ======================================

        tipo = None
        origem = None

        # ======================================
        # PRODUTO NÃO EXISTE NA NF
        # ======================================

        if codigo not in mapa_xml:

            tipo = TipoDivergencia.PRODUTO_A_MAIS
            origem = "FORA_NOTA"

        # ======================================
        # PRODUTO DA NF NÃO FOI CONTADO
        # ======================================

        elif codigo not in mapa_contagem:

            tipo = TipoDivergencia.PRODUTO_NAO_ENCONTRADO
            origem = "NOTA"

        # ======================================
        # QUANTIDADE MENOR
        # ======================================

        elif diferenca < 0:

            tipo = TipoDivergencia.QUANTIDADE_MENOR
            origem = "NOTA"

        # ======================================
        # QUANTIDADE MAIOR
        # ======================================

        elif diferenca > 0:

            tipo = TipoDivergencia.QUANTIDADE_MAIOR
            origem = "NOTA"

        # ======================================
        # SEM DIVERGÊNCIA
        # ======================================

        if tipo is None:

            divergencia_existente = (
                mapa_divergencias.get(codigo)
            )

            if divergencia_existente:

                db.delete(
                    divergencia_existente
                )

            resultado.append({
                "codigo": codigo,
                "xml": xml_qtd,
                "contado": cont_qtd,
                "diferenca": diferenca,
                "divergente": False,
                "divergencia_id": None,
                "tipo_divergencia": None,
                "justificado": False,
                "justificativa_tipo": None,
                "justificativa_descricao": None
            })

            continue

        # ======================================
        # EXISTE DIVERGÊNCIA
        # ======================================

        divergencia = mapa_divergencias.get(
            codigo
        )

        # ======================================
        # CRIAR NOVA DIVERGÊNCIA
        # ======================================

        if not divergencia:

            divergencia = Divergencia(
                conferencia_id=conferencia_id,
                codigo=codigo,
                xml=xml_qtd,
                contado=cont_qtd,
                diferenca=diferenca,
                tipo=tipo,
                origem=origem,
                versao=versao_atual
            )

            db.add(
                divergencia
            )

            # Garante que o ID seja gerado
            db.flush()

        # ======================================
        # ATUALIZAR DIVERGÊNCIA EXISTENTE
        # ======================================

        else:

            houve_alteracao = (
                divergencia.xml != xml_qtd
                or divergencia.contado != cont_qtd
                or divergencia.diferenca != diferenca
                or divergencia.tipo != tipo
                or divergencia.origem != origem
            )

            divergencia.xml = xml_qtd
            divergencia.contado = cont_qtd
            divergencia.diferenca = diferenca
            divergencia.tipo = tipo
            divergencia.origem = origem

            # Se a divergência mudou,
            # a justificativa anterior deixa de valer.

            if houve_alteracao:

                divergencia.justificativa_tipo = None

                divergencia.justificativa_descricao = None

        # ======================================
        # PREPARAR JUSTIFICATIVA
        # ======================================

        justificativa_tipo = None

        if divergencia.justificativa_tipo:

            justificativa_tipo = (
                divergencia.justificativa_tipo.value
                if hasattr(
                    divergencia.justificativa_tipo,
                    "value"
                )
                else str(
                    divergencia.justificativa_tipo
                )
            )

        # ======================================
        # ADICIONAR AO RESULTADO
        # ======================================

        resultado.append({
            "codigo": codigo,
            "xml": xml_qtd,
            "contado": cont_qtd,
            "diferenca": diferenca,
            "divergente": True,
            "divergencia_id": divergencia.id,
            "tipo_divergencia": (
                tipo.value
                if hasattr(
                    tipo,
                    "value"
                )
                else str(tipo)
            ),
            "justificado": (
                divergencia.justificativa_tipo
                is not None
            ),
            "justificativa_tipo": justificativa_tipo,
            "justificativa_descricao": (
                divergencia.justificativa_descricao
            )
        })

    # ==========================================
    # COMMIT
    # ==========================================

    db.commit()

    # ==========================================
    # TOTALIZADORES
    # ==========================================

    total_itens = len(
        resultado
    )

    divergentes = sum(
        1
        for item in resultado
        if item["divergente"]
    )

    # ==========================================
    # RETORNO
    # ==========================================

    return {
        "status": (
            "divergente"
            if divergentes > 0
            else "ok"
        ),

        "status_conferencia": (
            conferencia.status.value
            if hasattr(
                conferencia.status,
                "value"
            )
            else str(
                conferencia.status
            )
        ),

        "total_itens": total_itens,

        "divergentes": divergentes,

        "versao": versao_atual,

        "itens": resultado
    }


# ==========================================================
# FECHAR CONFERÊNCIA
# ==========================================================

def fechar_conferencia(
    db: Session,
    conferencia_id: int,
    usuario_id: int
):

    conferencia = db.query(
        Conferencia
    ).filter_by(
        id=conferencia_id
    ).first()

    if not conferencia:

        raise HTTPException(
            404,
            "Conferência não encontrada"
        )

    if conferencia.status == STATUS_FINALIZADA:

        return {
            "msg": "Conferência já está finalizada"
        }

    # ==========================================
    # SOMENTE DIVERGÊNCIAS DA VERSÃO ATUAL
    # ==========================================

    divergencias_sem_justificativa = db.query(
        Divergencia
    ).filter(
        Divergencia.conferencia_id == conferencia_id,
        Divergencia.versao == conferencia.versao,
        Divergencia.justificativa_tipo.is_(None)
    ).count()

    if divergencias_sem_justificativa > 0:

        raise HTTPException(
            400,
            "Existem divergências sem justificativa."
        )

    # ==========================================
    # FINALIZAR
    # ==========================================

    conferencia.status = (
        StatusConferencia.FINALIZADA
    )

    registrar_historico(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=usuario_id,
        acao="FINALIZADA",
        versao=conferencia.versao
    )

    db.commit()

    return {
        "msg": "Conferência finalizada com sucesso"
    }


# ==========================================================
# REABRIR CONFERÊNCIA
# ==========================================================

def reabrir_conferencia(
    db: Session,
    conferencia_id: int,
    usuario_id: int,
    motivo: str
):

    conferencia = db.query(
        Conferencia
    ).filter_by(
        id=conferencia_id
    ).first()

    if not conferencia:

        raise HTTPException(
            404,
            "Conferência não encontrada"
        )

    # ==========================================
    # MOTIVO OBRIGATÓRIO
    # ==========================================

    if not motivo or not motivo.strip():

        raise HTTPException(
            400,
            "Motivo obrigatório"
        )

    # ==========================================
    # STATUS QUE PERMITEM REABERTURA
    # ==========================================

    if conferencia.status not in [
        StatusConferencia.FINALIZADA,
        StatusConferencia.REPROVADA
    ]:

        raise HTTPException(
            400,
            "Status não permite reabertura"
        )

    # ==========================================
    # NOVA VERSÃO
    # ==========================================

    conferencia.status = (
        StatusConferencia.REABERTA
    )

    conferencia.quantidade_reaberturas += 1

    conferencia.versao += 1

    # ==========================================
    # REGISTRAR HISTÓRICO
    # ==========================================

    registrar_historico(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=usuario_id,
        acao="REABERTA",
        versao=conferencia.versao,
        motivo=motivo
    )

    db.commit()

    return {
        "msg": "Conferência reaberta com sucesso",

        "motivo": motivo,

        "versao": conferencia.versao,

        "quantidade_reaberturas": (
            conferencia.quantidade_reaberturas
        )
    }