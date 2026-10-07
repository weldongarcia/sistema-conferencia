"""
POST /login: senha Argon2id, senha legada (migração no primeiro login),
falhas indistinguíveis e contrato da resposta.
"""

import pytest

from argon2 import PasswordHasher

from app.core.security import (
    TAMANHO_MAXIMO_SENHA,
    decodificar_token,
    gerar_hash,
    precisa_rehash,
    verificar_senha,
)
from app.models.usuario import Usuario


FALHA = {"detail": "Credenciais inválidas"}


def login(client, username, senha):
    return client.post("/login", json={"username": username, "senha": senha})


def senha_gravada(db, usuario):
    db.expire_all()
    return db.get(Usuario, usuario.id).senha


# ============================================================
# SUCESSO
# ============================================================

def test_login_com_senha_hash_e_contrato(client_autenticado, fabrica):
    usuario = fabrica.usuario(
        username="maria",
        senha=gerar_hash("senha-da-maria"),
    )

    resposta = login(client_autenticado, "maria", "senha-da-maria")

    assert resposta.status_code == 200

    corpo = resposta.json()

    assert set(corpo) == {"access_token", "token_type", "usuario_id"}
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario_id"] == usuario.id
    assert decodificar_token(corpo["access_token"]) == "maria"
    assert "senha" not in resposta.text


def test_login_legado_migra_para_argon2id_no_primeiro_acesso(
    client_autenticado, db, fabrica
):
    usuario = fabrica.usuario(username="joao", senha="senha-antiga")

    resposta = login(client_autenticado, "joao", "senha-antiga")

    assert resposta.status_code == 200

    gravada = senha_gravada(db, usuario)

    assert gravada.startswith("$argon2id$")
    assert gravada != "senha-antiga"
    assert verificar_senha("senha-antiga", gravada)

    # O segundo login já usa o hash.
    assert login(client_autenticado, "joao", "senha-antiga").status_code == 200
    assert senha_gravada(db, usuario) == gravada


def test_login_regrava_hash_com_parametros_antigos(
    client_autenticado, db, fabrica
):
    fraco = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    usuario = fabrica.usuario(username="ana", senha=fraco.hash("senha"))

    assert login(client_autenticado, "ana", "senha").status_code == 200

    gravada = senha_gravada(db, usuario)

    assert not precisa_rehash(gravada)
    assert verificar_senha("senha", gravada)


# ============================================================
# FALHAS
# ============================================================

def test_senha_legada_incorreta_nao_altera(client_autenticado, db, fabrica):
    usuario = fabrica.usuario(username="pedro", senha="senha-antiga")

    resposta = login(client_autenticado, "pedro", "senha-errada")

    assert resposta.status_code == 401
    assert resposta.json() == FALHA
    assert senha_gravada(db, usuario) == "senha-antiga"


def test_senha_legada_incorreta_usa_hash_ficticio(
    client_autenticado, db, fabrica, monkeypatch
):
    # Sem o hash fictício, a falha da senha legada responderia em
    # fração de milissegundo e revelaria que o usuário existe.
    from app.services import auth_service

    chamadas = []
    original = auth_service.verificar_senha

    def espiao(senha, hash_armazenado):
        chamadas.append(hash_armazenado)
        return original(senha, hash_armazenado)

    monkeypatch.setattr(auth_service, "verificar_senha", espiao)

    usuario = fabrica.usuario(username="tempo", senha="senha-antiga")

    resposta = login(client_autenticado, "tempo", "senha-errada")

    assert resposta.status_code == 401
    assert resposta.json() == FALHA
    assert chamadas == [auth_service._HASH_FICTICIO]
    assert senha_gravada(db, usuario) == "senha-antiga"


def test_senha_hash_incorreta(client_autenticado, fabrica):
    fabrica.usuario(username="lia", senha=gerar_hash("correta"))

    resposta = login(client_autenticado, "lia", "errada")

    assert resposta.status_code == 401
    assert resposta.json() == FALHA


def test_usuario_inexistente_igual_a_senha_incorreta(
    client_autenticado, fabrica
):
    fabrica.usuario(username="existe", senha=gerar_hash("correta"))

    inexistente = login(client_autenticado, "nao-existe", "qualquer")
    senha_errada = login(client_autenticado, "existe", "qualquer")

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json() == FALHA


def test_formato_desconhecido_nunca_e_tratado_como_texto_puro(
    client_autenticado, db, fabrica
):
    valor = "$2b$12$" + "a" * 53
    usuario = fabrica.usuario(username="bcrypt", senha=valor)

    # Mesmo enviando exatamente o valor gravado.
    resposta = login(client_autenticado, "bcrypt", valor)

    assert resposta.status_code == 401
    assert resposta.json() == FALHA
    assert senha_gravada(db, usuario) == valor


def test_senha_acima_do_limite_retorna_401(client_autenticado, db, fabrica):
    longa = "a" * (TAMANHO_MAXIMO_SENHA + 1)
    usuario = fabrica.usuario(username="longa", senha=longa)

    resposta = login(client_autenticado, "longa", longa)

    assert resposta.status_code == 401
    assert resposta.json() == FALHA
    assert senha_gravada(db, usuario) == longa


def test_login_nao_imprime_senha_nem_token(
    client_autenticado, fabrica, capsys
):
    fabrica.usuario(username="silencio", senha="senha-que-nao-aparece")

    token = login(
        client_autenticado, "silencio", "senha-que-nao-aparece"
    ).json()["access_token"]

    login(client_autenticado, "silencio", "outra-senha-que-nao-aparece")

    saida = capsys.readouterr()
    texto = saida.out + saida.err

    assert "senha-que-nao-aparece" not in texto
    assert "outra-senha-que-nao-aparece" not in texto
    assert token not in texto
