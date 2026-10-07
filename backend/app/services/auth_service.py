"""
Autenticação por usuário e senha.

Estratégia de migração D (SEC-01A):
- senha Argon2id: verificação normal; o hash é regravado se os
  parâmetros do hasher mudaram;
- senha legada em texto puro: se correta, é convertida para
  Argon2id no mesmo login;
- formato desconhecido: login recusado (nunca tratado como texto puro).

Todas as falhas são indistinguíveis para o cliente.
"""

from sqlalchemy.orm import Session

from app.core.security import (
    SENHA_ARGON2ID,
    SENHA_LEGADA,
    _verificar_senha_legada_texto_puro_migracao,
    classificar_senha_armazenada,
    gerar_hash,
    precisa_rehash,
    senha_dentro_do_limite,
    verificar_senha,
)
from app.models.usuario import Usuario


# Hash de uma senha aleatória, usado apenas para gastar o mesmo
# tempo de verificação quando o usuário não existe.
_HASH_FICTICIO = gerar_hash("senha-ficticia-para-equalizar-tempo")


def autenticar(db: Session, username: str, senha: str):
    """
    Retorna o usuário autenticado ou None.

    Faz commit somente quando a senha armazenada precisa ser
    convertida ou regravada.
    """

    if not senha_dentro_do_limite(senha):
        return None

    usuario = (
        db.query(Usuario)
        .filter(Usuario.username == username)
        .first()
    )

    if usuario is None:
        verificar_senha(senha, _HASH_FICTICIO)
        return None

    formato = classificar_senha_armazenada(usuario.senha)

    if formato == SENHA_ARGON2ID:

        if not verificar_senha(senha, usuario.senha):
            return None

        if precisa_rehash(usuario.senha):
            usuario.senha = gerar_hash(senha)
            db.commit()

        return usuario

    if formato == SENHA_LEGADA:

        if not _verificar_senha_legada_texto_puro_migracao(
            senha,
            usuario.senha
        ):
            # Mesmo custo do caminho com hash: sem isso, a resposta
            # rápida revelaria que o usuário existe com senha legada.
            verificar_senha(senha, _HASH_FICTICIO)
            return None

        usuario.senha = gerar_hash(senha)
        db.commit()

        return usuario

    # Formato desconhecido: gasta o mesmo tempo e recusa.
    verificar_senha(senha, _HASH_FICTICIO)

    return None
