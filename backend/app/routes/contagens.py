from fastapi import APIRouter, Depends

from fastapi.security import HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal

from app.schemas.contagem import ContagemCreate

from app.services.contagem_services import (
    criar_contagem as criar_contagem_service
)

from app.core.security import (
    security,
    exigir_perfil
)

from app.utils.auth import get_current_user

from app.core.perfis import CONFERENTE

from app.schemas.sincronizacao import SincronizacaoContagem

from app.services.sincronizacao_service import (
    sincronizar_contagem
)


router = APIRouter(
    prefix="/contagens",
    tags=["Contagens"]
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


@router.post("/")
def criar_contagem(

    dados: ContagemCreate,

    db: Session = Depends(get_db),

    token: HTTPAuthorizationCredentials = Depends(
        security
    ),

    usuario=Depends(get_current_user)

):

    print("TIPO:", type(usuario))
    print("USUARIO:", usuario)

    exigir_perfil(
        usuario,
        [CONFERENTE]
    )

    return criar_contagem_service(
        db,
        dados,
        usuario
    )

@router.post("/sincronizar/{conferencia_id}")
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