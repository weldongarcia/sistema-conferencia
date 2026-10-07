"""
Hash de senha (Argon2id) e classificação do valor armazenado.
"""

import pytest

from argon2 import PasswordHasher

from app.core.security import (
    SENHA_ARGON2ID,
    SENHA_DESCONHECIDA,
    SENHA_LEGADA,
    TAMANHO_MAXIMO_SENHA,
    SenhaInvalida,
    _verificar_senha_legada_texto_puro_migracao,
    classificar_senha_armazenada,
    gerar_hash,
    precisa_rehash,
    verificar_senha,
)


def test_gera_hash_argon2id_com_parametros_rfc9106():
    valor = gerar_hash("senha-correta")

    assert valor.startswith("$argon2id$v=19$")
    assert "m=65536,t=3,p=4" in valor
    assert "senha-correta" not in valor


def test_verifica_senha_correta():
    assert verificar_senha("senha-correta", gerar_hash("senha-correta"))


def test_rejeita_senha_incorreta():
    assert not verificar_senha("senha-errada", gerar_hash("senha-correta"))


def test_salt_diferente_em_hashes_sucessivos():
    primeiro = gerar_hash("mesma-senha")
    segundo = gerar_hash("mesma-senha")

    assert primeiro != segundo
    assert verificar_senha("mesma-senha", primeiro)
    assert verificar_senha("mesma-senha", segundo)


def test_aceita_unicode():
    assert verificar_senha("çãõ-€-ü", gerar_hash("çãõ-€-ü"))


# ============================================================
# LIMITE DE TAMANHO
# ============================================================

def test_aceita_senha_no_limite():
    senha = "a" * TAMANHO_MAXIMO_SENHA

    assert verificar_senha(senha, gerar_hash(senha))


@pytest.mark.parametrize(
    "senha",
    ["", "a" * (TAMANHO_MAXIMO_SENHA + 1), None],
    ids=["vazia", "acima_do_limite", "none"],
)
def test_gerar_hash_rejeita_senha_fora_do_limite(senha):
    with pytest.raises(SenhaInvalida):
        gerar_hash(senha)


def test_verificar_rejeita_senha_acima_do_limite_sem_erro():
    valor = gerar_hash("a" * TAMANHO_MAXIMO_SENHA)

    assert not verificar_senha("a" * (TAMANHO_MAXIMO_SENHA + 1), valor)


def test_verificar_com_hash_invalido_retorna_false():
    assert not verificar_senha("qualquer", "nao-e-um-hash")
    assert not verificar_senha("qualquer", "$argon2id$corrompido")


# ============================================================
# REHASH
# ============================================================

def test_hash_atual_nao_precisa_rehash():
    assert not precisa_rehash(gerar_hash("senha"))


def test_hash_com_parametros_antigos_precisa_rehash():
    fraco = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)

    assert precisa_rehash(fraco.hash("senha"))


# ============================================================
# CLASSIFICAÇÃO DO VALOR ARMAZENADO
# ============================================================

@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, SENHA_DESCONHECIDA),
        ("", SENHA_DESCONHECIDA),
        ("$2b$12$" + "a" * 53, SENHA_DESCONHECIDA),
        ("$argon2i$v=19$m=65536,t=3,p=4$abc$def", SENHA_DESCONHECIDA),
        ("$qualquer", SENHA_DESCONHECIDA),
        ("senha-em-texto-puro", SENHA_LEGADA),
        ("123456", SENHA_LEGADA),
    ],
    ids=[
        "none",
        "vazio",
        "bcrypt",
        "argon2i",
        "cifrao",
        "texto_puro",
        "numerico",
    ],
)
def test_classificacao(valor, esperado):
    assert classificar_senha_armazenada(valor) == esperado


def test_classifica_argon2id():
    assert classificar_senha_armazenada(gerar_hash("x")) == SENHA_ARGON2ID


# ============================================================
# COMPATIBILIDADE DE MIGRAÇÃO
# ============================================================

def test_legado_aceita_somente_valor_identico():
    assert _verificar_senha_legada_texto_puro_migracao("abc123", "abc123")
    assert not _verificar_senha_legada_texto_puro_migracao("abc124", "abc123")
    assert not _verificar_senha_legada_texto_puro_migracao("ABC123", "abc123")
    assert not _verificar_senha_legada_texto_puro_migracao("", "")


def test_legado_rejeita_senha_acima_do_limite():
    senha = "a" * (TAMANHO_MAXIMO_SENHA + 1)

    assert not _verificar_senha_legada_texto_puro_migracao(senha, senha)
