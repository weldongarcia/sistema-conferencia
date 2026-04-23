from jose import jwt
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from passlib.context import CryptContext



from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def gerar_hash(senha: str):
    return pwd_context.hash(senha)

def verificar_senha(senha: str, hash: str):
    return pwd_context.verify(senha, hash)

security = HTTPBearer()


SECRET_KEY = 'sua-chave-secreta'
ALGORITHM = 'HS256'

def criar_token(usuario: str, perfil: str):
    return jwt.encode(
        {'sub': usuario, 'perfil': perfil},
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
            