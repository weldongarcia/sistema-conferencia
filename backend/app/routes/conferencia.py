from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.services.conferencia_service import comparar_conferencia
from app.core.perfis import AUDITOR
from app.core.security import exigir_perfil
from app.core.status import (STATUS_APROVADA,
     STATUS_REPROVADA,
     STATUS_REABERTA,
     STATUS_FINALIZADA,
     STATUS_ABERTA
)
from app.models.conferencia import Conferencia
from app.utils.auth import get_current_user



router = APIRouter(prefix="/conferencia", tags=["Conferencia"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{conferencia_id}")
def comparar(conferencia_id: int, db: Session = Depends(get_db)):
    return comparar_conferencia(db, conferencia_id)

@router.post("/{conferencia_id}/aprovar")
def aprovar_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):

    exigir_perfil(usuario, [AUDITOR])

    conferencia = db.query(Conferencia).filter_by(
        id=conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(404, "Conferência não encontrada")

    if conferencia.status != STATUS_FINALIZADA:
        raise HTTPException(
            400,
            'Somente conferências finalizadas podem ser aprovadas'
        )
    conferencia.status = STATUS_APROVADA

    db.commit()

    return {
        "msg": "Conferência aprovada"
    }

@router.post("/{conferencia_id}/reprovar")
def reprovar_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):

    exigir_perfil(usuario, [AUDITOR])

    conferencia = db.query(Conferencia).filter_by(
        id=conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(404, "Conferência não encontrada")


    if conferencia.status != STATUS_FINALIZADA:
        raise HTTPException(
            400,
            'Somente conferências finalizadas podem ser reprovadas'
        )
    conferencia.status = STATUS_REPROVADA

    db.commit()

    return {
        "msg": "Conferência reprovada"
    }

@router.post("/{conferencia_id}/reabrir")
def reabrir_conferencia(
    conferencia_id: int,
    motivo: str = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):

    exigir_perfil(usuario, [AUDITOR])

    conferencia = db.query(Conferencia).filter_by(
        id=conferencia_id
    ).first()

    if not conferencia:
        raise HTTPException(404, "Conferência não encontrada")

    if conferencia.status not in [
        STATUS_FINALIZADA,
        STATUS_REPROVADA
    ]:
        raise HTTPException(
            400,
            "Status não permite reabertura"
        )

    conferencia.status = STATUS_REABERTA
    conferencia.quantidade_reaberturas += 1

    db.commit()

    return {
        "msg": "Conferência reaberta",
        "motivo": motivo
    }