from fastapi import Request, HTTPException
from jose import jwt, JWTError
from app.database.connection import SessionLocal
from app.models.usuario import Usuario
from app.core.security import SECRET_KEY, ALGORITHM

def get_current_user(request: Request):

    authorization = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(401, "Token não informado")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Formato de token inválido")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError as e:
        print("ERRO JWT:", str(e))  # 👈 isso vai revelar o problema se ainda houver
        raise HTTPException(401, "Token inválido")

    db = SessionLocal()

    usuario = db.query(Usuario).filter(
        Usuario.username == username
    ).first()

    db.close()

    if not usuario:
        raise HTTPException(401, "Usuário não encontrado")

    return usuario