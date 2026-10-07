"""
GET /conferencia/{id} é somente leitura.

Três provas independentes, pela rota HTTP real:
1. nenhum INSERT, UPDATE ou DELETE emitido na engine;
2. nenhum commit na sessão da requisição e nenhum objeto
   pendente em session.new, session.dirty ou session.deleted;
3. fotografia de todas as tabelas idêntica antes e depois.
"""

import pytest

from sqlalchemy import event

from app.enums.conferencia_enums import (
    StatusConferencia,
    TipoDivergencia,
    TipoJustificativa,
)
from app.routes import conferencia as rota_conferencia

from conftest import fotografar_banco


# ============================================================
# MONITOR DE ESCRITA
# ============================================================

class Monitor:
    def __init__(self):
        self.ativo = False
        self.sql = {"INSERT": [], "UPDATE": [], "DELETE": []}
        self.commits = 0
        self.pendentes = []

    @staticmethod
    def estado(sessao):
        return {
            "new": list(sessao.new),
            "dirty": [o for o in sessao.dirty if sessao.is_modified(o)],
            "deleted": list(sessao.deleted),
        }


@pytest.fixture
def monitor(engine, app_teste, SessionTeste):
    monitor = Monitor()

    def antes_do_sql(conn, cursor, statement, params, context, many):
        if not monitor.ativo:
            return

        comando = statement.lstrip().split(None, 1)[0].upper()

        if comando in monitor.sql:
            monitor.sql[comando].append(statement)

    event.listen(engine, "before_cursor_execute", antes_do_sql)

    def get_db_monitorado():
        sessao = SessionTeste()

        def antes_do_commit(s):
            monitor.commits += 1
            monitor.pendentes.append(monitor.estado(s))

        event.listen(sessao, "before_commit", antes_do_commit)

        try:
            yield sessao
        finally:
            # Estado da sessão ao fim da requisição, antes do close.
            monitor.pendentes.append(monitor.estado(sessao))
            sessao.close()

    app_teste.dependency_overrides[rota_conferencia.get_db] = (
        get_db_monitorado
    )

    yield monitor

    event.remove(engine, "before_cursor_execute", antes_do_sql)


# ============================================================
# CENÁRIOS
#
# Cada cenário prepara os dados e devolve o que a resposta
# deve exibir por código: (divergente, tem_id, justificado).
# ============================================================

def cenario_consistente(fabrica, conferencia):
    # Divergência gravada e justificada que corresponde ao cálculo.
    fabrica.item_nf(conferencia, "30001", 5)
    fabrica.item_nf(conferencia, "30002", 3)
    fabrica.contagem(conferencia, "30001", 2)
    fabrica.contagem(conferencia, "30002", 3)

    fabrica.divergencia(
        conferencia, "30001", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Justificada",
    )

    return {
        "30001": (True, True, True),
        "30002": (False, False, False),
    }


def cenario_divergencia_ausente(fabrica, conferencia):
    # Legado: divergência calculada, mas nunca gravada.
    fabrica.item_nf(conferencia, "31001", 5)
    fabrica.contagem(conferencia, "31001", 2)

    return {
        "31001": (True, False, False),
    }


def cenario_divergencia_obsoleta(fabrica, conferencia):
    # 32001: gravada 5/2, contagem atual 5 -> deixou de divergir.
    # 32002: gravada 5/2, contagem atual 3 -> valores mudaram.
    fabrica.item_nf(conferencia, "32001", 5)
    fabrica.item_nf(conferencia, "32002", 5)
    fabrica.contagem(conferencia, "32001", 5)
    fabrica.contagem(conferencia, "32002", 3)

    for codigo in ("32001", "32002"):
        fabrica.divergencia(
            conferencia, codigo, xml=5, contado=2,
            tipo=TipoDivergencia.QUANTIDADE_MENOR,
            justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
            justificativa_descricao=f"Justificativa {codigo}",
        )

    return {
        "32001": (False, False, False),
        "32002": (True, False, False),
    }


def cenario_sem_xml(fabrica, conferencia):
    # Nenhum item de NF; apenas contagem.
    fabrica.contagem(conferencia, "33001", 2)

    return {
        "33001": (True, False, False),
    }


CENARIOS = {
    "consistente": cenario_consistente,
    "ausente": cenario_divergencia_ausente,
    "obsoleta_justificada": cenario_divergencia_obsoleta,
    "sem_xml": cenario_sem_xml,
}

STATUS = [
    StatusConferencia.RASCUNHO,
    StatusConferencia.REABERTA,
    StatusConferencia.FINALIZADA,
    StatusConferencia.APROVADA,
    StatusConferencia.REPROVADA,
]


# ============================================================
# TESTE
# ============================================================

@pytest.mark.parametrize("cenario", list(CENARIOS))
@pytest.mark.parametrize("status", STATUS, ids=[s.value for s in STATUS])
def test_get_nao_escreve(
    client, db, fabrica, usuario_atual, monitor, status, cenario
):
    usuario_atual.usuario = fabrica.usuario(
        perfil="CONFERENTE", estabelecimento_id=1
    )

    conferencia = fabrica.conferencia(status=status)

    esperado = CENARIOS[cenario](fabrica, conferencia)

    antes = fotografar_banco(db)

    monitor.ativo = True
    resposta = client.get(f"/conferencia/{conferencia.id}")
    monitor.ativo = False

    assert resposta.status_code == 200

    # 1. SQL de escrita
    assert monitor.sql["INSERT"] == []
    assert monitor.sql["UPDATE"] == []
    assert monitor.sql["DELETE"] == []

    # 2. Sessão
    assert monitor.commits == 0

    for estado in monitor.pendentes:
        assert estado == {"new": [], "dirty": [], "deleted": []}

    # 3. Banco
    assert fotografar_banco(db) == antes

    # Resposta
    itens = {item["codigo"]: item for item in resposta.json()["itens"]}

    assert set(itens) == set(esperado)

    for codigo, (divergente, tem_id, justificado) in esperado.items():
        item = itens[codigo]

        assert item["divergente"] is divergente, codigo
        assert (item["divergencia_id"] is not None) is tem_id, codigo
        assert item["justificado"] is justificado, codigo

        if not justificado:
            assert item["justificativa_tipo"] is None, codigo
            assert item["justificativa_descricao"] is None, codigo


# ============================================================
# EXIBIÇÃO DA DIVERGÊNCIA GRAVADA
# ============================================================

def test_exibe_divergencia_gravada_correspondente(
    client, fabrica, usuario_atual
):
    usuario_atual.usuario = fabrica.usuario()

    conferencia = fabrica.conferencia(status=StatusConferencia.APROVADA)

    fabrica.item_nf(conferencia, "34001", 5)
    fabrica.contagem(conferencia, "34001", 2)

    divergencia = fabrica.divergencia(
        conferencia, "34001", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_CADASTRO,
        justificativa_descricao="Cadastro antigo",
    )

    (item,) = client.get(f"/conferencia/{conferencia.id}").json()["itens"]

    assert item == {
        "codigo": "34001",
        "descricao": "Produto 34001",
        "xml": 5.0,
        "contado": 2.0,
        "diferenca": -3.0,
        "divergente": True,
        "divergencia_id": divergencia.id,
        "tipo_divergencia": "QUANTIDADE_MENOR",
        "justificado": True,
        "justificativa_tipo": "ERRO_CADASTRO",
        "justificativa_descricao": "Cadastro antigo",
    }


def test_exibe_divergencia_correspondente_entre_duplicadas(
    client, fabrica, usuario_atual
):
    # Mesma escolha de recalcular_divergencias: a justificada
    # mais antiga.
    usuario_atual.usuario = fabrica.usuario()

    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "34002", 5)
    fabrica.contagem(conferencia, "34002", 2)

    fabrica.divergencia(
        conferencia, "34002", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
    )
    justificada = fabrica.divergencia(
        conferencia, "34002", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.OUTROS,
        justificativa_descricao="Duplicada justificada",
    )

    (item,) = client.get(f"/conferencia/{conferencia.id}").json()["itens"]

    assert item["divergencia_id"] == justificada.id
    assert item["justificado"] is True
