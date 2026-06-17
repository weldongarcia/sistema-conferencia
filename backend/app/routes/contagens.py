from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.schemas.contagem import ContagemCreate
from app.services.contagem_services import criar_contagem as criar_contagem_service


from app.core.security import (
    verificar_token,
    security,
    exigir_perfil
)

from app.utils.auth import get_current_user
from app.core.perfis import CONFERENTE, AUDITOR

router = APIRouter(prefix="/contagens", tags=["Contagens"])

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
    token: HTTPAuthorizationCredentials = Depends(security),
    usuario = Depends(get_current_user)
):
    print("TIPO:", type(usuario))
    print("USUARIO:", usuario)

    exigir_perfil(usuario, [CONFERENTE])

    return criar_contagem_service(
        db,
        dados,
        usuario
    )

