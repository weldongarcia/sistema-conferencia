from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.schemas.conferencia_schema import (
    ConferenciaCreate,
    ConferenciaResponse
)

from app.services.conferencia_crud import criar_conferencia

from app.models.conferencia import Conferencia

from app.utils.auth import get_current_user


router = APIRouter()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# LISTAR CONFERÊNCIAS
# ============================================================

@router.get(
    "/conferencias",
    response_model=list[ConferenciaResponse]
)
def listar_conferencias(
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    # --------------------------------------------------------
    # AUDITOR
    # --------------------------------------------------------
    # Auditor pode visualizar todas as conferências.
    # --------------------------------------------------------

    if usuario.perfil == "AUDITOR":
        return (
            db.query(Conferencia)
            .order_by(Conferencia.id.desc())
            .all()
        )

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

        return (
            db.query(Conferencia)
            .filter(
                Conferencia.estabelecimento_id
                == usuario.estabelecimento_id
            )
            .order_by(Conferencia.id.desc())
            .all()
        )

    # --------------------------------------------------------
    # PERFIL NÃO AUTORIZADO
    # --------------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail="Perfil não autorizado."
    )


# ============================================================
# CRIAR CONFERÊNCIA
# ============================================================

@router.post(
    "/conferencias",
    response_model=ConferenciaResponse
)
def criar(
    dados: ConferenciaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user)
):

    # Somente conferente pode criar conferência
    if usuario.perfil != "CONFERENTE":
        raise HTTPException(
            status_code=403,
            detail="Somente conferentes podem criar conferências."
        )

    if usuario.estabelecimento_id is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Usuário não está vinculado a um "
                "estabelecimento."
            )
        )

    try:
        return criar_conferencia(
            db=db,
            dados=dados,
            usuario=usuario
        )

    except ValueError as e:
        raise HTTPException(
            status_code=403,
            detail=str(e)
        )


    # --------------------------------------------------------
    # AUDITOR
    # --------------------------------------------------------
    # Não permitimos que o fechamento seja usado como
    # mecanismo para atravessar o isolamento das lojas.
    # O fluxo de auditoria continuará nas rotas específicas.
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

    elif usuario.perfil != "AUDITOR":

        raise HTTPException(
            status_code=403,
            detail="Perfil não autorizado."
        )

    return fechar_conferencia(
        db=db,
        conferencia_id=conferencia_id,
        usuario_id=usuario.id
    )