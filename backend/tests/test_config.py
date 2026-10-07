"""
Configuração lida do ambiente (SECRET_KEY e DATABASE_URL).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core import config
from app.core.config import (
    ConfiguracaoInvalida,
    carregar_arquivo_env,
    carregar_configuracao,
)


CHAVE_VALIDA = "k" * 32
URL = "postgresql://usuario:senha@host:5432/banco"


def test_configuracao_valida():
    cfg = carregar_configuracao({
        "SECRET_KEY": CHAVE_VALIDA,
        "DATABASE_URL": URL,
    })

    assert cfg.secret_key == CHAVE_VALIDA
    assert cfg.database_url == URL


@pytest.mark.parametrize(
    "ambiente",
    [
        {"DATABASE_URL": URL},
        {"SECRET_KEY": "", "DATABASE_URL": URL},
        {"SECRET_KEY": "   ", "DATABASE_URL": URL},
    ],
    ids=["ausente", "vazia", "espacos"],
)
def test_secret_key_obrigatoria(ambiente):
    with pytest.raises(ConfiguracaoInvalida, match="SECRET_KEY não definida"):
        carregar_configuracao(ambiente)


def test_rejeita_chave_antiga_publicada():
    with pytest.raises(ConfiguracaoInvalida, match="publicado"):
        carregar_configuracao({
            "SECRET_KEY": "sua-chave-secreta",
            "DATABASE_URL": URL,
        })


def test_rejeita_secret_key_curta():
    with pytest.raises(ConfiguracaoInvalida, match="32 caracteres"):
        carregar_configuracao({
            "SECRET_KEY": "k" * 31,
            "DATABASE_URL": URL,
        })


@pytest.mark.parametrize(
    "ambiente",
    [{"SECRET_KEY": CHAVE_VALIDA}, {"SECRET_KEY": CHAVE_VALIDA, "DATABASE_URL": ""}],
    ids=["ausente", "vazia"],
)
def test_database_url_obrigatoria(ambiente):
    with pytest.raises(ConfiguracaoInvalida, match="DATABASE_URL"):
        carregar_configuracao(ambiente)


def test_erros_e_repr_nao_expoem_valores():
    curta = "segredo-curto-123"

    with pytest.raises(ConfiguracaoInvalida) as erro:
        carregar_configuracao({"SECRET_KEY": curta, "DATABASE_URL": URL})

    assert curta not in str(erro.value)

    cfg = carregar_configuracao({
        "SECRET_KEY": CHAVE_VALIDA,
        "DATABASE_URL": URL,
    })

    assert CHAVE_VALIDA not in repr(cfg)
    assert "senha" not in repr(cfg)


# ============================================================
# ARQUIVO .env
# ============================================================

def test_env_nao_sobrescreve_variaveis_existentes(tmp_path, monkeypatch):
    arquivo = tmp_path / ".env"
    arquivo.write_text(
        "SEC01A_TESTE_EXISTENTE=do-arquivo\n"
        "SEC01A_TESTE_NOVA=do-arquivo\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("SEC01A_TESTE_EXISTENTE", "do-ambiente")
    monkeypatch.delenv("SEC01A_TESTE_NOVA", raising=False)

    try:
        assert carregar_arquivo_env(arquivo) is True

        assert os.environ["SEC01A_TESTE_EXISTENTE"] == "do-ambiente"
        assert os.environ["SEC01A_TESTE_NOVA"] == "do-arquivo"
    finally:
        os.environ.pop("SEC01A_TESTE_NOVA", None)


def test_env_inexistente(tmp_path):
    assert carregar_arquivo_env(tmp_path / "nao-existe.env") is False


def test_env_example_nao_contem_segredos():
    exemplo = Path(config.__file__).resolve().parents[2] / ".env.example"

    linhas = {
        chave: valor
        for chave, _, valor in (
            linha.partition("=")
            for linha in exemplo.read_text(encoding="utf-8").splitlines()
            if linha and not linha.startswith("#")
        )
    }

    assert linhas == {"SECRET_KEY": "", "DATABASE_URL": ""}


# ============================================================
# USO PELA APLICAÇÃO
# ============================================================

def test_database_url_vem_da_configuracao():
    from app.database.connection import engine

    assert config.configuracao.database_url == os.environ["DATABASE_URL"]
    assert str(engine.url) == config.configuracao.database_url


def test_aplicacao_falha_na_inicializacao_sem_secret_key():
    if config.ARQUIVO_ENV.is_file():
        pytest.skip("backend/.env existe e forneceria a SECRET_KEY")

    ambiente = {
        chave: valor
        for chave, valor in os.environ.items()
        if chave not in {"SECRET_KEY", "DATABASE_URL"}
    }
    ambiente["DATABASE_URL"] = "sqlite://"
    ambiente["PYTHONIOENCODING"] = "utf-8"

    resultado = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=Path(config.__file__).resolve().parents[2],
        env=ambiente,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert resultado.returncode != 0
    assert "ConfiguracaoInvalida" in resultado.stderr
    assert "SECRET_KEY não definida" in resultado.stderr
