from jose import jwt
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta

from app.core.permissoes import PERMISSOES


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


security = HTTPBearer()


SECRET_KEY = "sua-chave-secreta"
ALGORITHM = "HS256"


def gerar_hash(senha: str):
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str):
    return pwd_context.verify(senha, hash)


def criar_token(username: str, perfil: str):

    expire = datetime.utcnow() + timedelta(hours=8)

    payload = {
        "sub": username,
        "perfil": perfil,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verificar_token(token: str):

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return {
            "usuario": payload.get("sub"),
            "perfil": payload.get("perfil")
        }

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )


def exigir_permissao(perfil: str, acao: str):

    permissoes = PERMISSOES.get(perfil, [])

    if acao not in permissoes:
        raise HTTPException(
            status_code=403,
            detail=f"Perfil '{perfil}' não pode executar '{acao}'"
        )


def exigir_perfil(usuario, perfis_permitidos: list):

    if usuario.perfil not in perfis_permitidos:
        raise HTTPException(
            status_code=403,
            detail="Sem permissão"
        )