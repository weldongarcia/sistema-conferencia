from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.database.connection import SessionLocal
from app.models.usuario import Usuario
from app.core.security import TokenInvalido, decodificar_token, security
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    # Assinatura, HS256, exp e sub obrigatórios. O token e o motivo
    # da falha não são registrados.
    try:
        username = decodificar_token(token)
    except TokenInvalido:
        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )

    db = SessionLocal()

    try:
        usuario = db.query(Usuario).filter(
            Usuario.username == username
        ).first()

        # Mesma resposta de um token inválido. O perfil efetivo vem
        # do banco, nunca do claim do token.
        if not usuario:
            raise HTTPException(
                status_code=401,
                detail="Token inválido"
            )

        return usuario

    finally:
        db.close()
