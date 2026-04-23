from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest
from app.core.security import verificar_senha, criar_token

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(dados: LoginRequest, db: Session = Depends(get_db)):

    usuario = db.query(Usuario).filter_by(username=dados.username).first()

    if not usuario:
        raise HTTPException(400, "Usuário não encontrado")

    if not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(400, "Senha inválida")

    return {
        "access_token": criar_token(usuario.username, usuario.perfil)
    }
