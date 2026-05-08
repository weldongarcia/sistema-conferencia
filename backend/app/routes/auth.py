from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginSchema
from app.core.security import criar_token

router = APIRouter()

@router.post("/login")
def login(dados: LoginSchema, db: Session = Depends(get_db)):

    usuario = db.query(Usuario).filter(
        Usuario.username == dados.username
    ).first()

    if not usuario or usuario.senha != dados.senha:
        raise HTTPException(401, "Credenciais inválidas")

    token = criar_token(usuario.username, usuario.perfil)

    return {
        "access_token": token,
        "token_type": "bearer"
    }
