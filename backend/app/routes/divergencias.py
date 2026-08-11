from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.conferencia import Conferencia
from app.models.divergencia import Divergencia

from app.database.connection import SessionLocal

from app.utils.auth import get_current_user

from app.core.perfis import CONFERENTE
from app.core.security import exigir_perfil

from app.enums.conferencia_enums import StatusConferencia

from app.schemas.divergencia import JustificarDivergencia

from app.services.conferencia_historico_service import (
    registrar_historico
)
router = APIRouter(
    prefix="/divergencias",
    tags=["Divergências"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        from app.core.perfis import CONFERENTE
from app.core.security import exigir_perfil


@router.post("/{divergencia_id}/justificar")
def justificar_divergencia(
    divergencia_id: int,
    dados: JustificarDivergencia,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    # ==========================================
    # PERFIL
    # ==========================================

    exigir_perfil(usuario, [CONFERENTE])

    # ==========================================
    # BUSCAR DIVERGÊNCIA
    # ==========================================

    divergencia = db.query(Divergencia).filter(
        Divergencia.id == divergencia_id
    ).first()

    if not divergencia:
        raise HTTPException(
            404,
            "Divergência não encontrada"
        )

    # ==========================================
    # BUSCAR CONFERÊNCIA
    # ==========================================

    conferencia = db.query(Conferencia).filter(
        Conferencia.id == divergencia.conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(
            404,
            "Conferência não encontrada"
        )

    # ==========================================
    # VERIFICAR VERSÃO
    # ==========================================

    if divergencia.versao != conferencia.versao:
        raise HTTPException(
            400,
            "Esta divergência pertence a uma versão anterior "
            "da conferência."
        )

    # ==========================================
    # CONFERÊNCIA NÃO PODE ESTAR FINALIZADA
    # ==========================================

    if conferencia.status == StatusConferencia.FINALIZADA:
        raise HTTPException(
            400,
            "Não é possível justificar divergência "
            "de uma conferência finalizada."
        )

    # ==========================================
    # VALIDAR TIPO
    # ==========================================

    if dados.justificativa_tipo is None:
        raise HTTPException(
            400,
            "Tipo da justificativa é obrigatório."
        )

    # ==========================================
    # VALIDAR DESCRIÇÃO
    # ==========================================

    if (
        not dados.justificativa_descricao
        or not dados.justificativa_descricao.strip()
    ):
        raise HTTPException(
            400,
            "Descrição da justificativa é obrigatória."
        )

    # ==========================================
    # REGISTRAR JUSTIFICATIVA
    # ==========================================

    divergencia.justificativa_tipo = (
        dados.justificativa_tipo
    )

    divergencia.justificativa_descricao = (
        dados.justificativa_descricao.strip()
    )

    # ==========================================
    # HISTÓRICO
    # ==========================================

    registrar_historico(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=usuario.id,
        acao="DIVERGENCIA_JUSTIFICADA",
        versao=conferencia.versao,
        motivo=(
            f"Produto {divergencia.codigo} | "
            f"Tipo: {dados.justificativa_tipo} | "
            f"{dados.justificativa_descricao.strip()}"
        )
    )

    db.commit()

    return {
        "msg": "Divergência justificada com sucesso",
        "divergencia_id": divergencia.id,
        "conferencia_id": conferencia.id,
        "versao": conferencia.versao
    }

@router.get("/{conferencia_id}")
def listar_divergencias(
    conferencia_id: int,
    db: Session = Depends(get_db)
):

    divergencias = db.query(Divergencia).filter_by(
        conferencia_id=conferencia_id
    ).all()

    return divergencias