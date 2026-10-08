from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.item_nf import ItemNF
from app.models.contagem import Contagem
from app.models.divergencia import Divergencia
from app.models.conferencia import Conferencia

from app.enums.conferencia_enums import (
    StatusConferencia
)

from app.services.conferencia_historico_service import registrar_historico
from app.services.estado_conferencia import (
    Operacao,
    exigir_operacao_permitida
)
from app.services.divergencia_service import (
    calcular_comparacao,
    divergencia_corresponde,
    escolher_divergencia,
    recalcular_divergencias
)
from app.utils.codigo import normalizar_codigo


# A aprovação recalcula a versão FINALIZADA antes de validar.
ESTADOS_RECALCULO_APROVACAO = frozenset({
    StatusConferencia.FINALIZADA,
})


# ==========================================================
# COMPARAR CONFERÊNCIA
# ==========================================================

def comparar_conferencia(
    db,
    conferencia_id,
    usuario
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

    # ======================================================
    # ISOLAMENTO POR ESTABELECIMENTO
    # ======================================================

    if usuario.perfil == "CONFERENTE":

        if usuario.estabelecimento_id is None:
            raise HTTPException(
                403,
                "Usuário não está vinculado a um estabelecimento."
            )

        if (
            conferencia.estabelecimento_id
            != usuario.estabelecimento_id
        ):
            raise HTTPException(
                403,
                "Você não possui acesso a esta conferência."
            )

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
    # DIVERGÊNCIAS GRAVADAS DA VERSÃO ATUAL
    #
    # Somente leitura: o GET não cria, atualiza nem
    # remove divergências. Elas são mantidas pelos
    # fluxos de escrita (recalcular_divergencias).
    # ==========================================

    divergencias_existentes = db.query(
        Divergencia
    ).filter(
        Divergencia.conferencia_id == conferencia_id,
        Divergencia.versao == versao_atual
    ).order_by(
        Divergencia.id
    ).all()

    gravadas_por_codigo = defaultdict(list)

    for d in divergencias_existentes:
        gravadas_por_codigo[
            normalizar_codigo(d.codigo)
        ].append(d)

    mapa_divergencias = {
        codigo: escolher_divergencia(gravadas)
        for codigo, gravadas in gravadas_por_codigo.items()
    }

    # ==========================================
    # RESULTADO
    # ==========================================

    resultado = []

    comparacao = calcular_comparacao(
        itens_nf,
        contagens
    )

    for item in comparacao:

        # ======================================
        # SEM DIVERGÊNCIA
        # ======================================

        if not item.divergente:

            resultado.append({
                "codigo": item.codigo,
                "descricao": item.descricao,
                "xml": item.xml,
                "contado": item.contado,
                "diferenca": item.diferenca,
                "divergente": False,
                "divergencia_id": None,
                "tipo_divergencia": None,
                "justificado": False,
                "justificativa_tipo": None,
                "justificativa_descricao": None
            })

            continue

        # ======================================
        # DIVERGÊNCIA GRAVADA CORRESPONDENTE
        #
        # Ausente ou obsoleta: a divergência calculada
        # é exibida sem id e sem justificativa, até o
        # próximo recálculo de um fluxo de escrita.
        # ======================================

        divergencia = mapa_divergencias.get(
            item.codigo
        )

        if (
            divergencia is not None
            and not divergencia_corresponde(divergencia, item)
        ):
            divergencia = None

        justificativa_tipo = None

        if divergencia is not None and divergencia.justificativa_tipo:

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

        resultado.append({
            "codigo": item.codigo,
            "descricao": item.descricao,
            "xml": item.xml,
            "contado": item.contado,
            "diferenca": item.diferenca,
            "divergente": True,
            "divergencia_id": (
                divergencia.id
                if divergencia is not None
                else None
            ),
            "tipo_divergencia": item.tipo.value,
            "justificado": justificativa_tipo is not None,
            "justificativa_tipo": justificativa_tipo,
            "justificativa_descricao": (
                divergencia.justificativa_descricao
                if divergencia is not None
                else None
            )
        })

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

    # Somente RASCUNHO e REABERTA. APROVADA e REPROVADA não voltam
    # para FINALIZADA; FINALIZADA não é fechada de novo.
    exigir_operacao_permitida(
        conferencia,
        Operacao.FECHAR
    )

    # ==========================================
    # RECALCULAR ANTES DE VALIDAR
    #
    # O fechamento decide sobre o estado real das
    # contagens, sem depender de um GET anterior.
    #
    # O commit grava o recálculo mesmo quando o
    # fechamento é bloqueado abaixo: as divergências
    # pendentes precisam existir (com id) para serem
    # justificadas.
    # ==========================================

    resumo = recalcular_divergencias(
        db,
        conferencia
    )

    if resumo.houve_alteracao:
        db.commit()

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

    # ======================================================
    # MOTIVO OBRIGATÓRIO
    # ======================================================

    if not motivo or not motivo.strip():

        raise HTTPException(
            400,
            "O motivo da reabertura é obrigatório."
        )

    # ======================================================
    # STATUS QUE PERMITEM REABERTURA
    # ======================================================

    exigir_operacao_permitida(
        conferencia,
        Operacao.REABRIR
    )

    # ======================================================
    # NOVA VERSÃO
    # ======================================================

    conferencia.versao += 1

    # ======================================================
    # CONTADOR DE REABERTURAS
    # ======================================================

    conferencia.quantidade_reaberturas += 1

    # ======================================================
    # ALTERAR STATUS
    # ======================================================

    conferencia.status = (
        StatusConferencia.REABERTA
    )

    # ======================================================
    # DIVERGÊNCIAS DA NOVA VERSÃO
    #
    # Nascem sem justificativa. As da versão anterior
    # permanecem intactas.
    #
    # Executado antes de registrar_historico, que faz o
    # commit, para que tudo fique na mesma transação.
    # ======================================================

    recalcular_divergencias(
        db,
        conferencia
    )

    # ======================================================
    # REGISTRAR HISTÓRICO
    # ======================================================

    registrar_historico(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=usuario_id,
        acao="REABERTA",
        versao=conferencia.versao,
        motivo=motivo.strip()
    )

    # ======================================================
    # SALVAR
    # ======================================================

    db.commit()

    db.refresh(
        conferencia
    )

    return {
        "msg": "Conferência reaberta com sucesso",

        "conferencia_id": conferencia.id,

        "status": conferencia.status.value,

        "versao": conferencia.versao,

        "quantidade_reaberturas": (
            conferencia.quantidade_reaberturas
        )
    }


# ==========================================================
# APROVAR CONFERÊNCIA
# ==========================================================

def aprovar_conferencia(
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

    # ==========================================
    # STATUS OBRIGATÓRIO
    # ==========================================

    exigir_operacao_permitida(
        conferencia,
        Operacao.APROVAR
    )

    # ==========================================
    # RECALCULAR ANTES DE VALIDAR
    #
    # A aprovação não confia nas divergências
    # gravadas: recalcula a versão em auditoria na
    # mesma transação. Se ficar pendência, a
    # transação é desfeita e nada é gravado; a
    # conferência continua FINALIZADA e precisa ser
    # reaberta para correção.
    # ==========================================

    recalcular_divergencias(
        db,
        conferencia,
        estados_permitidos=ESTADOS_RECALCULO_APROVACAO
    )

    # ==========================================
    # DIVERGÊNCIAS DA VERSÃO ATUAL
    # ==========================================

    divergencias_sem_justificativa = db.query(
        Divergencia
    ).filter(
        Divergencia.conferencia_id == conferencia_id,
        Divergencia.versao == conferencia.versao,
        Divergencia.justificativa_tipo.is_(None)
    ).count()

    # ==========================================
    # BLOQUEAR APROVAÇÃO
    # ==========================================

    if divergencias_sem_justificativa > 0:

        db.rollback()

        raise HTTPException(
            400,
            (
                "Não é possível aprovar a conferência. "
                f"Existem {divergencias_sem_justificativa} "
                "divergência(s) sem justificativa."
            )
        )

    # ==========================================
    # APROVAR
    # ==========================================

    conferencia.status = (
        StatusConferencia.APROVADA
    )

    # ==========================================
    # HISTÓRICO
    # ==========================================

    registrar_historico(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=usuario_id,
        acao="APROVADA",
        versao=conferencia.versao
    )

    db.commit()

    return {
        "msg": "Conferência aprovada com sucesso",
        "status": conferencia.status.value,
        "versao": conferencia.versao
    }


# ==========================================================
# REPROVAR CONFERÊNCIA
# ==========================================================

def reprovar_conferencia(
    db: Session,
    conferencia_id: int,
    usuario_id: int,
    motivo: str | None
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

    # ======================================================
    # MOTIVO OBRIGATÓRIO
    # ======================================================

    motivo = motivo.strip() if isinstance(motivo, str) else ""

    if not motivo:

        raise HTTPException(
            400,
            "O motivo da reprovação é obrigatório."
        )

    # ======================================================
    # STATUS OBRIGATÓRIO
    # ======================================================

    exigir_operacao_permitida(
        conferencia,
        Operacao.REPROVAR
    )

    # ======================================================
    # REPROVAR
    # ======================================================

    conferencia.status = (
        StatusConferencia.REPROVADA
    )

    registrar_historico(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=usuario_id,
        acao="REPROVADA",
        versao=conferencia.versao,
        motivo=motivo
    )

    db.commit()

    return {
        "msg": "Conferência reprovada"
    }
