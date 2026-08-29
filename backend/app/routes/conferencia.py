from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal

from app.services.conferencia_service import (
    comparar_conferencia,
    fechar_conferencia,
    reabrir_conferencia,
    aprovar_conferencia as aprovar_conferencia_service
)

from app.core.perfis import AUDITOR
from app.core.security import exigir_perfil

from app.models.conferencia import Conferencia
from app.models.conferencia_historico import ConferenciaHistorico
from app.models.contagem_historico import ContagemHistorico

from app.utils.auth import get_current_user
from app.enums.conferencia_enums import StatusConferencia

from app.services.conferencia_historico_service import (
    registrar_historico
)


router = APIRouter(
    prefix="/conferencia",
    tags=["Conferencia"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# FUNÇÃO AUXILIAR
# ============================================================

def verificar_acesso_conferencia(
    conferencia: Conferencia,
    usuario
):
    """
    Verifica se o usuário possui acesso à conferência.

    AUDITOR:
        Pode acessar qualquer conferência.

    CONFERENTE:
        Pode acessar somente conferências do seu estabelecimento.

    A função apenas valida o acesso.
    Ela não executa nenhuma operação adicional.
    """

    # --------------------------------------------------------
    # AUDITOR
    # --------------------------------------------------------

    if usuario.perfil == AUDITOR:
        return

    # --------------------------------------------------------
    # CONFERENTE
    # --------------------------------------------------------

    if usuario.perfil == "CONFERENTE":

        if usuario.estabelecimento_id is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Usuário não está vinculado a um "
                    "estabelecimento."
                )
            )

        if (
            conferencia.estabelecimento_id
            != usuario.estabelecimento_id
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Você não possui acesso a esta "
                    "conferência."
                )
            )

        return

    # --------------------------------------------------------
    # PERFIL NÃO AUTORIZADO
    # --------------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail="Perfil não autorizado."
    )


# ============================================================
# FECHAR CONFERÊNCIA
# ============================================================

@router.post("/{conferencia_id}/fechar")
def fechar_conferencia_endpoint(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    conferencia = (
        db.query(Conferencia)
        .filter(
            Conferencia.id == conferencia_id
        )
        .first()
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    # --------------------------------------------------------
    # FECHAMENTO É OPERAÇÃO DO CONFERENTE
    # --------------------------------------------------------

    if usuario.perfil != "CONFERENTE":
        raise HTTPException(
            status_code=403,
            detail=(
                "Somente o conferente pode fechar "
                "a conferência."
            )
        )

    # --------------------------------------------------------
    # VERIFICAR ACESSO À LOJA
    # --------------------------------------------------------

    verificar_acesso_conferencia(
        conferencia,
        usuario
    )

    return fechar_conferencia(
        db=db,
        conferencia_id=conferencia_id,
        usuario_id=usuario.id
    )


# ============================================================
# COMPARAR / VISUALIZAR CONFERÊNCIA
# ============================================================

@router.get("/{conferencia_id}")
def comparar(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    conferencia = (
        db.query(Conferencia)
        .filter(
            Conferencia.id == conferencia_id
        )
        .first()
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    # --------------------------------------------------------
    # VERIFICAR ACESSO
    # --------------------------------------------------------

    verificar_acesso_conferencia(
        conferencia,
        usuario
    )

    return comparar_conferencia(
        db,
        conferencia_id,
        usuario
    )


# ============================================================
# APROVAR CONFERÊNCIA
# ============================================================

@router.post("/{conferencia_id}/aprovar")
def aprovar_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    # --------------------------------------------------------
    # SOMENTE AUDITOR
    # --------------------------------------------------------

    exigir_perfil(
        usuario,
        [AUDITOR]
    )

    # --------------------------------------------------------
    # APROVAÇÃO CENTRALIZADA NO SERVICE
    # --------------------------------------------------------

    return aprovar_conferencia_service(
        db=db,
        conferencia_id=conferencia_id,
        usuario_id=usuario.id
    )


# ============================================================
# REPROVAR CONFERÊNCIA
# ============================================================

@router.post("/{conferencia_id}/reprovar")
def reprovar_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    exigir_perfil(
        usuario,
        [AUDITOR]
    )

    conferencia = (
        db.query(Conferencia)
        .filter(
            Conferencia.id == conferencia_id
        )
        .first()
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    if conferencia.status != StatusConferencia.FINALIZADA:
        raise HTTPException(
            status_code=400,
            detail=(
                "Somente conferências finalizadas "
                "podem ser reprovadas."
            )
        )

    conferencia.status = StatusConferencia.REPROVADA

    registrar_historico(
        db=db,
        conferencia_id=conferencia_id,
        usuario_id=usuario.id,
        acao="REPROVADA",
        versao=conferencia.versao
    )

    db.commit()

    return {
        "msg": "Conferência reprovada"
    }


# ============================================================
# REABRIR CONFERÊNCIA
# ============================================================

@router.post("/{conferencia_id}/reabrir")
def reabrir_conferencia_endpoint(
    conferencia_id: int,
    motivo: str = Body(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    exigir_perfil(
        usuario,
        [AUDITOR]
    )

    return reabrir_conferencia(
        db=db,
        conferencia_id=conferencia_id,
        usuario_id=usuario.id,
        motivo=motivo
    )


# ============================================================
# HISTÓRICO
# ============================================================

@router.get("/{conferencia_id}/historico")
def historico_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    conferencia = (
        db.query(Conferencia)
        .filter(
            Conferencia.id == conferencia_id
        )
        .first()
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    verificar_acesso_conferencia(
        conferencia,
        usuario
    )

    historico = (
        db.query(ConferenciaHistorico)
        .filter_by(
            conferencia_id=conferencia_id
        )
        .order_by(
            ConferenciaHistorico.id.desc()
        )
        .all()
    )

    return historico


# ============================================================
# TIMELINE
# ============================================================

@router.get("/{conferencia_id}/timeline")
def timeline_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    conferencia = (
        db.query(Conferencia)
        .filter(
            Conferencia.id == conferencia_id
        )
        .first()
    )

    if not conferencia:
        raise HTTPException(
            status_code=404,
            detail="Conferência não encontrada."
        )

    verificar_acesso_conferencia(
        conferencia,
        usuario
    )

    historico_conferencia = (
        db.query(ConferenciaHistorico)
        .filter_by(
            conferencia_id=conferencia_id
        )
        .all()
    )

    historico_contagens = (
        db.query(ContagemHistorico)
        .filter_by(
            conferencia_id=conferencia_id
        )
        .all()
    )

    eventos = []

    # ========================================================
    # EVENTOS DA CONFERÊNCIA
    # ========================================================

    for item in historico_conferencia:

        descricao = {
            "FINALIZADA": "Conferência finalizada",
            "APROVADA": "Conferência aprovada",
            "REPROVADA": "Conferência reprovada",
            "REABERTA": "Conferência reaberta",
            "DIVERGENCIA_JUSTIFICADA": (
                "Divergência justificada"
            )
        }.get(
            item.acao,
            item.acao
        )

        eventos.append({
            "data": item.data_evento,
            "usuario": item.usuario.username,
            "evento": descricao,
            "versao": item.versao,
            "motivo": item.motivo
        })

    # ========================================================
    # EVENTOS DAS CONTAGENS
    # ========================================================

    for item in historico_contagens:

        eventos.append({
            "data": item.data_alteracao,
            "usuario": item.usuario.username,
            "evento": (
                f"Produto {item.codigo} "
                f"alterado de {item.valor_anterior} "
                f"para {item.valor_novo}"
            ),
            "versao": item.versao
        })

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    eventos.sort(
        key=lambda x: x["data"],
        reverse=True
    )

    return eventos