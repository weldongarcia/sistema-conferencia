"""
Script de migração de senhas legadas (backend/scripts/migrar_senhas.py).

Executado somente sobre o banco SQLite de teste.
"""

import pytest

from sqlalchemy import event

from app.core.security import (
    TAMANHO_MAXIMO_SENHA,
    gerar_hash,
    verificar_senha,
)
from app.models.usuario import Usuario

from scripts import migrar_senhas as script

from conftest import fotografar


SENHAS_LEGADAS = {
    "legado1": "senha-legada-um",
    "legado2": "senha-legada-dois",
}

LONGA = "x" * (TAMANHO_MAXIMO_SENHA + 1)
BCRYPT = "$2b$12$" + "b" * 53


@pytest.fixture
def base(fabrica):
    """Cria a base mista e devolve os usuários por username."""

    usuarios = {}

    for username, senha in SENHAS_LEGADAS.items():
        usuarios[username] = fabrica.usuario(username=username, senha=senha)

    usuarios["hash"] = fabrica.usuario(
        username="hash", senha=gerar_hash("ja-migrada")
    )
    usuarios["bcrypt"] = fabrica.usuario(username="bcrypt", senha=BCRYPT)
    usuarios["longa"] = fabrica.usuario(username="longa", senha=LONGA)

    return usuarios


def senhas(db):
    db.expire_all()
    return {u.username: u.senha for u in db.query(Usuario)}


# ============================================================
# DRY-RUN
# ============================================================

def test_dry_run_nao_altera(db, base):
    antes = fotografar(db, Usuario)

    commits = []

    def registrar(sessao):
        commits.append(1)

    event.listen(db, "after_commit", registrar)

    try:
        relatorio = script.executar(db)
    finally:
        event.remove(db, "after_commit", registrar)

    assert relatorio.aplicado is False
    assert commits == []
    assert fotografar(db, Usuario) == antes

    assert relatorio.total == 5
    assert relatorio.ja_argon2id == 1
    assert sorted(relatorio.legadas_migradas) == sorted(
        base[u].id for u in SENHAS_LEGADAS
    )
    assert relatorio.legadas_fora_do_limite == [base["longa"].id]
    assert relatorio.formato_desconhecido == [base["bcrypt"].id]


def test_main_padrao_e_dry_run(SessionTeste, db, base, capsys):
    antes = fotografar(db, Usuario)

    assert script.main([], sessao_factory=SessionTeste) == 0

    saida = capsys.readouterr().out

    assert "DRY-RUN (nada foi gravado)" in saida
    assert "--apply" in saida
    assert fotografar(db, Usuario) == antes


# ============================================================
# APPLY
# ============================================================

def test_apply_migra_somente_legadas(db, base):
    hash_existente = base["hash"].senha

    script.executar(db, aplicar=True)

    gravadas = senhas(db)

    for username, senha in SENHAS_LEGADAS.items():
        assert gravadas[username].startswith("$argon2id$")
        assert verificar_senha(senha, gravadas[username])

    # Inalterados.
    assert gravadas["hash"] == hash_existente
    assert gravadas["bcrypt"] == BCRYPT
    assert gravadas["longa"] == LONGA


def test_main_apply(SessionTeste, db, base, capsys):
    assert script.main(["--apply"], sessao_factory=SessionTeste) == 0

    assert "APLICADO" in capsys.readouterr().out
    assert senhas(db)["legado1"].startswith("$argon2id$")


def test_segunda_execucao_nao_altera(db, base):
    primeira = script.executar(db, aplicar=True)
    depois = fotografar(db, Usuario)

    segunda = script.executar(db, aplicar=True)

    assert len(primeira.legadas_migradas) == 2
    assert segunda.legadas_migradas == []
    assert segunda.ja_argon2id == 3
    assert fotografar(db, Usuario) == depois


def test_erro_desfaz_tudo(db, base, monkeypatch):
    antes = fotografar(db, Usuario)

    chamadas = []
    original = script.gerar_hash

    def gerar_com_falha(senha):
        chamadas.append(1)

        if len(chamadas) == 2:
            raise RuntimeError("falha simulada")

        return original(senha)

    monkeypatch.setattr(script, "gerar_hash", gerar_com_falha)

    with pytest.raises(RuntimeError):
        script.executar(db, aplicar=True)

    assert len(chamadas) == 2
    assert fotografar(db, Usuario) == antes


def test_main_erro_retorna_1_sem_detalhes(
    SessionTeste, db, base, monkeypatch, capsys
):
    def falhar(senha):
        raise RuntimeError(f"detalhe sensível {senha}")

    monkeypatch.setattr(script, "gerar_hash", falhar)

    assert script.main(["--apply"], sessao_factory=SessionTeste) == 1

    erro = capsys.readouterr().err

    assert "nenhuma alteração foi gravada" in erro
    assert "detalhe sensível" not in erro

    for senha in SENHAS_LEGADAS.values():
        assert senha not in erro


# ============================================================
# NADA SENSÍVEL É IMPRESSO
# ============================================================

@pytest.mark.parametrize("argumentos", [[], ["--apply"]], ids=["dry", "apply"])
def test_nao_imprime_senhas_hashes_nem_usernames(
    SessionTeste, db, base, capsys, argumentos
):
    hash_existente = base["hash"].senha

    script.main(argumentos, sessao_factory=SessionTeste)

    saida = capsys.readouterr()
    texto = saida.out + saida.err

    for senha in (*SENHAS_LEGADAS.values(), LONGA, BCRYPT, hash_existente):
        assert senha not in texto

    for valor in senhas(db).values():
        assert valor not in texto

    assert "$argon2" not in texto
    assert "$2b$" not in texto

    for username in base:
        assert username not in texto
