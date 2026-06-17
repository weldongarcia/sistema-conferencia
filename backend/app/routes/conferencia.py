from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.services.conferencia_service import comparar_conferencia
from app.core.perfis import AUDITOR
from app.core.security import exigir_perfil
from app.models.conferencia_historico import ConferenciaHistorico
from app.models.contagem_historico import ContagemHistorico
from app.core.status import (STATUS_APROVADA,
     STATUS_REPROVADA,
     STATUS_REABERTA,
     STATUS_FINALIZADA,
     STATUS_ABERTA
)
from app.models.conferencia import Conferencia
from app.utils.auth import get_current_user
from app.enums.conferencia_enums import StatusConferencia
from app.services.conferencia_historico_service import registrar_historico
from app.models.conferencia_historico import ConferenciaHistorico


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

    if conferencia.status != StatusConferencia.FINALIZADA:
        raise HTTPException(
            400,
            'Somente conferências finalizadas podem ser aprovadas'
        )
    conferencia.status = StatusConferencia.APROVADA

    registrar_historico(
        db=db,
        conferencia_id=conferencia_id,
        usuario_id=usuario.id,
        acao="APROVADA",
        versao=conferencia.versao
    )

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


    if conferencia.status != StatusConferencia.FINALIZADA:
        raise HTTPException(
            400,
            'Somente conferências finalizadas podem ser reprovadas'
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
        StatusConferencia.FINALIZADA,
        StatusConferencia.REPROVADA
    ]:
        raise HTTPException(
            400,
            "Status não permite reabertura"
        )

    conferencia.status = StatusConferencia.REABERTA
    conferencia.quantidade_reaberturas += 1
    conferencia.versao += 1

    registrar_historico(
    db=db,
    conferencia_id=conferencia.id,
    usuario_id=usuario.id,
    acao="REABERTA",
    versao=conferencia.versao,
    motivo=motivo
)

    db.commit()

    return {
        "msg": "Conferência reaberta",
        "motivo": motivo
    }

@router.get("/{conferencia_id}/historico")
def historico_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db)
):

    historico = db.query(
        ConferenciaHistorico
    ).filter_by(
        conferencia_id=conferencia_id
    ).order_by(
        ConferenciaHistorico.id.desc()
    ).all()

    return historico

@router.get("/{conferencia_id}/timeline")
def timeline_conferencia(
    conferencia_id: int,
    db: Session = Depends(get_db)
):
    historico_conferencia = db.query(
        ConferenciaHistorico
    ).filter_by(
        conferencia_id=conferencia_id
    ).all()

    historico_contagens = db.query(
        ContagemHistorico
    ).filter_by(
        conferencia_id=conferencia_id
    ).all()

    eventos = []

    for item in historico_conferencia:
        eventos.append({
            "tipo": "CONFERENCIA",
            "data": item.data_evento,
            "usuario_id": item.usuario_id,
            "acao": item.acao,
            "versao": item.versao,
            "motivo": item.motivo

        })
    for item in historico_contagens:
        eventos.append({
            "tipo": "CONTAGEM",
            "data": item.data_alteracao,
            "usuario_id": item.usuario_id,
            "codigo": item.codigo,
            "valor_anterior": item.valor_anterior,
            "valor_novo": item.valor_novo,
            "versao": item.versao
        })

    eventos.sort(
        key=lambda x: x["data"],
        reverse=True
    )

    return eventos