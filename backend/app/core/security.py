import hmac
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.profiles import RFC_9106_LOW_MEMORY
from jose import jwt, JWTError
from fastapi import HTTPException
from fastapi.security import HTTPBearer

from app.core.config import configuracao
from app.core.permissoes import PERMISSOES


security = HTTPBearer()


# ==========================================================
# SENHAS — ARGON2ID
#
# Configuração única do hasher (RFC 9106, perfil de baixa
# memória: t=3, m=64 MiB, p=4). Alterar o perfil faz os
# hashes antigos serem regravados no próximo login
# (check_needs_rehash).
# ==========================================================

_hasher = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)

PREFIXO_ARGON2ID = "$argon2id$"

TAMANHO_MAXIMO_SENHA = 128

# Classificação do valor gravado em usuarios.senha.
SENHA_ARGON2ID = "ARGON2ID"
SENHA_LEGADA = "LEGADA"
SENHA_DESCONHECIDA = "DESCONHECIDA"


class SenhaInvalida(ValueError):
    pass


def senha_dentro_do_limite(senha) -> bool:
    return (
        isinstance(senha, str)
        and 0 < len(senha) <= TAMANHO_MAXIMO_SENHA
    )


def gerar_hash(senha: str) -> str:
    if not senha_dentro_do_limite(senha):
        raise SenhaInvalida(
            "A senha deve ter entre 1 e "
            f"{TAMANHO_MAXIMO_SENHA} caracteres."
        )

    return _hasher.hash(senha)


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    if not senha_dentro_do_limite(senha):
        return False

    try:
        return _hasher.verify(hash_armazenado, senha)
    except (VerificationError, InvalidHashError):
        return False


def precisa_rehash(hash_armazenado: str) -> bool:
    return _hasher.check_needs_rehash(hash_armazenado)


def classificar_senha_armazenada(valor) -> str:
    """
    ARGON2ID:     hash atual.
    DESCONHECIDA: vazio ou qualquer formato de hash ($...) que não
                  seja Argon2id. Nunca é tratado como texto puro.
    LEGADA:       texto puro anterior ao SEC-01A.
    """

    if not isinstance(valor, str) or not valor:
        return SENHA_DESCONHECIDA

    if valor.startswith(PREFIXO_ARGON2ID):
        return SENHA_ARGON2ID

    if valor.startswith("$"):
        return SENHA_DESCONHECIDA

    return SENHA_LEGADA


# ==========================================================
# COMPATIBILIDADE DE MIGRAÇÃO — REMOVER APÓS A MIGRAÇÃO
#
# Senhas gravadas em texto puro antes do SEC-01A. Usado
# somente pelo login para converter a senha no primeiro
# acesso. Comparação em tempo constante.
# ==========================================================

def _verificar_senha_legada_texto_puro_migracao(
    senha: str,
    valor_armazenado: str
) -> bool:

    if not senha_dentro_do_limite(senha):
        return False

    return hmac.compare_digest(
        senha.encode("utf-8"),
        valor_armazenado.encode("utf-8"),
    )


# ==========================================================
# JWT
# ==========================================================

ALGORITHM = "HS256"

EXPIRACAO_TOKEN = timedelta(hours=8)


class TokenInvalido(Exception):
    pass


def criar_token(username: str, perfil: str):

    expire = datetime.now(timezone.utc) + EXPIRACAO_TOKEN

    payload = {
        "sub": username,
        # Informativo: o perfil efetivo é sempre lido do banco.
        "perfil": perfil,
        "exp": expire
    }

    return jwt.encode(
        payload,
        configuracao.secret_key,
        algorithm=ALGORITHM
    )


def decodificar_token(token: str) -> str:
    """
    Valida assinatura, algoritmo (somente HS256), expiração e
    sub. Retorna o username. exp e sub são obrigatórios.
    """

    try:
        payload = jwt.decode(
            token,
            configuracao.secret_key,
            algorithms=[ALGORITHM],
            options={
                "require_exp": True,
                "require_sub": True,
            },
        )
    except JWTError as erro:
        raise TokenInvalido() from erro

    username = payload.get("sub")

    if not isinstance(username, str) or not username:
        raise TokenInvalido()

    return username


def verificar_token(token: str):

    try:
        payload = jwt.decode(
            token,
            configuracao.secret_key,
            algorithms=[ALGORITHM],
            options={
                "require_exp": True,
                "require_sub": True,
            },
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
