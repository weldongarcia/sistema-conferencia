from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import verificar_token, security, exigir_perfil
from app.database.connection import SessionLocal
from app.schemas.contagem import ContagemCreate
from app.services.contagem_services import criar_contagem
from app.core.security import verificar_token, security
from app.utils.auth import get_current_user
from app.core.perfis import CONFERENTE
from app.core.security import exigir_perfil
from fastapi import HTTPException
from app.core.perfis import AUDITOR

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
    token: str = Depends(security),
    usuario = Depends(get_current_user)
):
    exigir_perfil(usuario, [CONFERENTE])
    
    return criar_contagem_service(db, dados, usuario.username)

    usuario = dados_token["usuario"]
    perfil = dados_token['perfil']

    def exigir_perfil(usuario, perfis_permitidos):

       if usuario.perfil not in perfis_permitidos:
           raise HTTPException(
               status_code=403,
               detail='Sem permissao'
           )
       
