"""
Infraestrutura de testes do backend.

Os testes usam SQLite em memória e montam somente os routers
necessários. O app/main.py não é importado porque executa
create_all no PostgreSQL durante a importação.
"""

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base

# Registra todas as tabelas no metadata.
from app.models.usuario import Usuario
from app.models.conferencia import Conferencia
from app.models.conferencia_historico import ConferenciaHistorico
from app.models.contagem import Contagem
from app.models.contagem_historico import ContagemHistorico
from app.models.divergencia import Divergencia
from app.models.item_nf import ItemNF
from app.models.nota_fiscal import NotaFiscal
from app.models.produto import Produto

from app.enums.conferencia_enums import StatusConferencia
from app.utils.auth import get_current_user

from app.routes import conferencia as rota_conferencia


TABELAS_RASTREADAS = (
    Conferencia,
    ConferenciaHistorico,
    Contagem,
    ContagemHistorico,
    Divergencia,
    ItemNF,
    NotaFiscal,
)


# ============================================================
# BANCO
# ============================================================

@pytest.fixture
def engine():
    # StaticPool: o TestClient executa a rota em outra thread,
    # e o banco em memória precisa ser a mesma conexão.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    engine.dispose()


@pytest.fixture
def SessionTeste(engine):
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


@pytest.fixture
def db(SessionTeste):
    sessao = SessionTeste()

    yield sessao

    sessao.close()


# ============================================================
# DADOS
# ============================================================

class Fabrica:
    """Cria registros de teste já persistidos."""

    def __init__(self, db):
        self.db = db

    def _salvar(self, objeto):
        self.db.add(objeto)
        self.db.commit()
        self.db.refresh(objeto)
        return objeto

    def usuario(
        self,
        perfil="CONFERENTE",
        estabelecimento_id=1,
        username=None,
    ):
        total = self.db.query(Usuario).count()

        return self._salvar(Usuario(
            username=username or f"usuario{total + 1}",
            senha="hash-de-teste",
            perfil=perfil,
            estabelecimento_id=estabelecimento_id,
        ))

    def conferencia(
        self,
        status=StatusConferencia.RASCUNHO,
        versao=1,
        estabelecimento_id=1,
        usuario_id=1,
        quantidade_reaberturas=0,
    ):
        return self._salvar(Conferencia(
            estabelecimento_id=estabelecimento_id,
            usuario_id=usuario_id,
            status=status,
            versao=versao,
            quantidade_reaberturas=quantidade_reaberturas,
        ))

    def item_nf(
        self,
        conferencia,
        codigo,
        quantidade,
        descricao=None,
    ):
        return self._salvar(ItemNF(
            conferencia_id=conferencia.id,
            codigo=codigo,
            quantidade=str(quantidade),
            descricao=descricao or f"Produto {codigo}",
        ))

    def contagem(self, conferencia, codigo, quantidade):
        return self._salvar(Contagem(
            conferencia_id=conferencia.id,
            codigo=codigo,
            quantidade=quantidade,
        ))

    def divergencia(
        self,
        conferencia,
        codigo,
        xml,
        contado,
        tipo,
        origem="NOTA",
        versao=None,
        justificativa_tipo=None,
        justificativa_descricao=None,
    ):
        return self._salvar(Divergencia(
            conferencia_id=conferencia.id,
            codigo=codigo,
            xml=xml,
            contado=contado,
            diferenca=contado - xml,
            tipo=tipo,
            origem=origem,
            versao=versao if versao is not None else conferencia.versao,
            justificativa_tipo=justificativa_tipo,
            justificativa_descricao=justificativa_descricao,
        ))


@pytest.fixture
def fabrica(db):
    return Fabrica(db)


# ============================================================
# FOTOGRAFIA DO BANCO
# ============================================================

def fotografar(sessao, modelo, *filtros):
    """
    Retorna todas as colunas de todas as linhas do modelo,
    ordenadas por id, para comparação antes/depois.
    """

    colunas = [c.key for c in inspect(modelo).column_attrs]

    sessao.expire_all()

    linhas = (
        sessao.query(modelo)
        .filter(*filtros)
        .order_by(modelo.id)
        .all()
    )

    return [
        tuple(getattr(linha, coluna) for coluna in colunas)
        for linha in linhas
    ]


def fotografar_banco(sessao):
    return {
        modelo.__tablename__: fotografar(sessao, modelo)
        for modelo in TABELAS_RASTREADAS
    }


# ============================================================
# API
# ============================================================

class UsuarioAtual:
    """Permite trocar o usuário autenticado dentro do teste."""

    def __init__(self):
        self.usuario = None


@pytest.fixture
def usuario_atual():
    return UsuarioAtual()


@pytest.fixture
def app_teste(SessionTeste, usuario_atual):
    app = FastAPI()

    app.include_router(rota_conferencia.router)

    def get_db_teste():
        sessao = SessionTeste()

        try:
            yield sessao
        finally:
            sessao.close()

    def get_usuario_teste():
        return usuario_atual.usuario

    app.dependency_overrides[rota_conferencia.get_db] = get_db_teste
    app.dependency_overrides[get_current_user] = get_usuario_teste

    return app


@pytest.fixture
def client(app_teste):
    with TestClient(app_teste) as cliente:
        yield cliente
