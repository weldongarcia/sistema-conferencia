from jose import jwt
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from app.core.permissoes import PERMISSOES
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi.security import HTTPBearer


def exigir_permissao(perfil: str, acao: str):
    permissoes = PERMISSOES.get(perfil, [])

    if acao not in permissoes:
        raise HTTPException(
            status_code=403,
            detail=f"Perfil '{perfil}' não pode executar '{acao}'"
        )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def gerar_hash(senha: str):
    return pwd_context.hash(senha)

def verificar_senha(senha: str, hash: str):
    return pwd_context.verify(senha, hash)

security = HTTPBearer()


SECRET_KEY = 'sua-chave-secreta'
ALGORITHM = 'HS256'
security = HTTPBearer()

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "usuario": payload.get("sub"),
            "perfil": payload.get("perfil")
        }
    except:
        raise HTTPException(401, "Token inválido")
    
def exigir_perfil(perfil_usuario: str, perfis_permitidos: list):
    if perfil_usuario not in perfis_permitidos:
        raise HTTPException(status_code=403, detail="Sem permissão")
            

def exigir_perfil(usuario, perfis_permitidos):

    if usuario.perfil not in perfis_permitidos:
        raise HTTPException(
            status_code=403,
            detail='Sem permissão'
        )