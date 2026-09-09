from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal

from app.schemas.sincronizacao import SincronizacaoContagem

from app.services.sincronizacao_service import (
    sincronizar_contagem
)

from app.utils.auth import get_current_user

from app.core.perfis import CONFERENTE

from app.core.security import exigir_perfil


router = APIRouter(
    prefix="/conferencias",
    tags=["Sincronização"]
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@router.post("/{conferencia_id}/sincronizar")
def sincronizar_conferencia(

    conferencia_id: int,

    dados: SincronizacaoContagem,

    db: Session = Depends(get_db),

    usuario=Depends(get_current_user)

):

    exigir_perfil(
        usuario,
        [CONFERENTE]
    )

    return sincronizar_contagem(
        db,
        conferencia_id,
        dados,
        usuario
    )