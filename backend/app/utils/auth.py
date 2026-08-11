from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from jose import jwt, JWTError

from app.database.connection import SessionLocal
from app.models.usuario import Usuario
from app.core.security import SECRET_KEY, ALGORITHM, security


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if not username:
            raise HTTPException(
                status_code=401,
                detail="Token inválido"
            )

    except JWTError as e:
        print("ERRO JWT:", str(e))

        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )

    db = SessionLocal()

    try:
        usuario = db.query(Usuario).filter(
            Usuario.username == username
        ).first()

        if not usuario:
            raise HTTPException(
                status_code=401,
                detail="Usuário não encontrado"
            )

        return usuario

    finally:
        db.close()