from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.auth import LoginSchema
from app.core.security import criar_token
from app.services.auth_service import autenticar

router = APIRouter()

@router.post("/login")
def login(dados: LoginSchema, db: Session = Depends(get_db)):

    usuario = autenticar(db, dados.username, dados.senha)

    # Mesma resposta para usuário inexistente e senha incorreta.
    if not usuario:
        raise HTTPException(401, "Credenciais inválidas")

    token = criar_token(usuario.username, usuario.perfil)

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario_id": usuario.id
    }
