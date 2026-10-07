"""
Configuração do backend lida do ambiente.

Variáveis obrigatórias (sem valor padrão):

- SECRET_KEY:   chave de assinatura do JWT (mínimo de 32 caracteres).
- DATABASE_URL: URL de conexão do SQLAlchemy.

Em desenvolvimento, backend/.env é carregado se existir. Variáveis já
definidas no ambiente têm prioridade e nunca são sobrescritas pelo
arquivo. Ver backend/.env.example.

A aplicação falha na importação deste módulo se a configuração for
inválida. Mensagens de erro nunca incluem o valor das variáveis.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv


ARQUIVO_ENV = Path(__file__).resolve().parents[2] / ".env"

TAMANHO_MINIMO_SECRET_KEY = 32

# Valor que esteve no código-fonte e foi publicado no repositório.
SECRET_KEYS_PROIBIDAS = frozenset({"sua-chave-secreta"})


class ConfiguracaoInvalida(RuntimeError):
    pass


@dataclass(frozen=True)
class Configuracao:
    secret_key: str
    database_url: str

    def __repr__(self):
        # Nunca expor segredos em logs ou tracebacks.
        return "Configuracao(secret_key=***, database_url=***)"


def carregar_arquivo_env(caminho: Path = ARQUIVO_ENV) -> bool:
    """
    Carrega o arquivo .env sem sobrescrever variáveis existentes.
    Retorna True se o arquivo existia.
    """

    if not caminho.is_file():
        return False

    load_dotenv(caminho, override=False)

    return True


def carregar_configuracao(ambiente: Mapping[str, str]) -> Configuracao:
    secret_key = (ambiente.get("SECRET_KEY") or "").strip()
    database_url = (ambiente.get("DATABASE_URL") or "").strip()

    if not secret_key:
        raise ConfiguracaoInvalida(
            "SECRET_KEY não definida. Configure a variável de ambiente "
            "(ver backend/.env.example)."
        )

    if secret_key in SECRET_KEYS_PROIBIDAS:
        raise ConfiguracaoInvalida(
            "SECRET_KEY usa um valor que já foi publicado no código-fonte. "
            "Gere uma nova chave."
        )

    if len(secret_key) < TAMANHO_MINIMO_SECRET_KEY:
        raise ConfiguracaoInvalida(
            f"SECRET_KEY deve ter pelo menos "
            f"{TAMANHO_MINIMO_SECRET_KEY} caracteres."
        )

    if not database_url:
        raise ConfiguracaoInvalida(
            "DATABASE_URL não definida. Configure a variável de ambiente "
            "(ver backend/.env.example)."
        )

    return Configuracao(
        secret_key=secret_key,
        database_url=database_url,
    )


carregar_arquivo_env()

configuracao = carregar_configuracao(os.environ)
