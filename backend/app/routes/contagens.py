from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import verificar_token, security, exigir_perfil

from app.database.connection import SessionLocal
from app.schemas.contagem import ContagemCreate
from app.services.contagem_services import criar_contagem
from app.core.security import verificar_token, security

router = APIRouter(prefix="/contagens", tags=["Contagens"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def criar(
    dados: ContagemCreate,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    dados_token = verificar_token(token)

    usuario = dados_token["usuario"]
    perfil = dados_token['perfil']

    exigir_perfil(perfil, ['admin', 'conferente'])