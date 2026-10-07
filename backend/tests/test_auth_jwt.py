"""
Validação do JWT em get_current_user (via GET /usuario/me e rotas
protegidas).
"""

import base64
import json
import time
from datetime import datetime, timezone

import pytest

from jose import jwt

from app.core.config import configuracao
from app.core.security import EXPIRACAO_TOKEN, criar_token
from app.enums.conferencia_enums import StatusConferencia

from conftest import cabecalho_token


TOKEN_INVALIDO = {"detail": "Token inválido"}


def assinar(claims, chave=None, algoritmo="HS256"):
    return jwt.encode(
        claims,
        chave or configuracao.secret_key,
        algorithm=algoritmo,
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def exp_futuro():
    return int(time.time()) + 3600


def me(client, headers):
    return client.get("/usuario/me", headers=headers)


# ============================================================
# TOKEN VÁLIDO
# ============================================================

def test_token_valido(client_autenticado, fabrica):
    usuario = fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=3)

    resposta = me(client_autenticado, cabecalho_token(usuario))

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": usuario.id,
        "username": usuario.username,
        "perfil": "CONFERENTE",
        "estabelecimento_id": 3,
    }


def test_token_expira_em_8_horas(fabrica):
    usuario = fabrica.usuario()

    claims = jwt.get_unverified_claims(
        criar_token(usuario.username, usuario.perfil)
    )

    restante = claims["exp"] - datetime.now(timezone.utc).timestamp()

    assert claims["sub"] == usuario.username
    assert abs(restante - EXPIRACAO_TOKEN.total_seconds()) < 60
    assert jwt.get_unverified_header(
        criar_token(usuario.username, usuario.perfil)
    )["alg"] == "HS256"


# ============================================================
# TOKENS REJEITADOS
# ============================================================

def test_token_expirado(client_autenticado, fabrica):
    usuario = fabrica.usuario()

    token = assinar({"sub": usuario.username, "exp": int(time.time()) - 5})

    resposta = me(client_autenticado, bearer(token))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


def test_token_sem_exp(client_autenticado, fabrica):
    usuario = fabrica.usuario()

    resposta = me(client_autenticado, bearer(assinar({"sub": usuario.username})))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


def test_token_sem_sub(client_autenticado):
    resposta = me(client_autenticado, bearer(assinar({"exp": exp_futuro()})))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


def test_token_com_sub_vazio(client_autenticado):
    token = assinar({"sub": "", "exp": exp_futuro()})

    assert me(client_autenticado, bearer(token)).status_code == 401


def test_assinatura_invalida(client_autenticado, fabrica):
    usuario = fabrica.usuario()

    token = assinar(
        {"sub": usuario.username, "exp": exp_futuro()},
        chave="outra-chave-com-mais-de-32-caracteres!!",
    )

    resposta = me(client_autenticado, bearer(token))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


def test_chave_antiga_publicada_rejeitada(client_autenticado, fabrica):
    auditor = fabrica.usuario(perfil="AUDITOR", estabelecimento_id=None)

    token = assinar(
        {"sub": auditor.username, "exp": exp_futuro()},
        chave="sua-chave-secreta",
    )

    resposta = me(client_autenticado, bearer(token))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


def test_alg_none(client_autenticado, fabrica):
    usuario = fabrica.usuario()

    def b64(dados):
        return base64.urlsafe_b64encode(
            json.dumps(dados).encode()
        ).rstrip(b"=").decode()

    token = (
        b64({"alg": "none", "typ": "JWT"})
        + "."
        + b64({"sub": usuario.username, "exp": exp_futuro()})
        + "."
    )

    resposta = me(client_autenticado, bearer(token))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


def test_algoritmo_diferente_de_hs256(client_autenticado, fabrica):
    usuario = fabrica.usuario()

    token = assinar(
        {"sub": usuario.username, "exp": exp_futuro()},
        algoritmo="HS512",
    )

    resposta = me(client_autenticado, bearer(token))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


def test_usuario_inexistente_no_token(client_autenticado):
    token = assinar({"sub": "nao-existe", "exp": exp_futuro()})

    resposta = me(client_autenticado, bearer(token))

    assert resposta.status_code == 401
    assert resposta.json() == TOKEN_INVALIDO


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer abc"}],
    ids=["sem_header", "basic", "malformado"],
)
def test_sem_token_ou_malformado(client_autenticado, headers):
    assert me(client_autenticado, headers).status_code == 401


# ============================================================
# PERFIL VEM DO BANCO
# ============================================================

def test_perfil_adulterado_no_token_nao_eleva_privilegio(
    client_autenticado, fabrica
):
    conferente = fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=1)
    conferencia = fabrica.conferencia(status=StatusConferencia.FINALIZADA)

    # Assinado com a chave correta, mas com perfil falso no claim.
    token = assinar({
        "sub": conferente.username,
        "perfil": "AUDITOR",
        "exp": exp_futuro(),
    })

    assert me(client_autenticado, bearer(token)).json()["perfil"] == (
        "CONFERENTE"
    )

    resposta = client_autenticado.post(
        f"/conferencia/{conferencia.id}/aprovar",
        headers=bearer(token),
    )

    assert resposta.status_code == 403


def test_falha_de_token_nao_e_impressa(client_autenticado, fabrica, capsys):
    usuario = fabrica.usuario()

    token = assinar(
        {"sub": usuario.username, "exp": exp_futuro()},
        chave="outra-chave-com-mais-de-32-caracteres!!",
    )

    me(client_autenticado, bearer(token))

    saida = capsys.readouterr()

    assert token not in saida.out + saida.err
    assert saida.out == ""
