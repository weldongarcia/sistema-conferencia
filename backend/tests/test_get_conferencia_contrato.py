"""
Caracterização do contrato de GET /conferencia/{id}.

Estes testes registram a resposta consumida pelo painel
(services/api.ts) e pelo coletor (ConferenciaResumo.fromJson)
e devem continuar passando durante a BACKEND-01.1.
"""

import pytest

from app.enums.conferencia_enums import (
    StatusConferencia,
    TipoDivergencia,
    TipoJustificativa,
)


CHAVES_RESPOSTA = {
    "status",
    "status_conferencia",
    "total_itens",
    "divergentes",
    "versao",
    "itens",
}

CHAVES_ITEM = {
    "codigo",
    "descricao",
    "xml",
    "contado",
    "diferenca",
    "divergente",
    "divergencia_id",
    "tipo_divergencia",
    "justificado",
    "justificativa_tipo",
    "justificativa_descricao",
}


@pytest.fixture
def conferente(fabrica, usuario_atual):
    usuario = fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=1)
    usuario_atual.usuario = usuario
    return usuario


@pytest.fixture
def auditor(fabrica):
    return fabrica.usuario(perfil="AUDITOR", estabelecimento_id=None)


def itens_por_codigo(resposta):
    return {item["codigo"]: item for item in resposta["itens"]}


def cenario_completo(fabrica):
    """
    10001: confere          (NF 10, contado 10)
    10002: quantidade menor (NF 5,  contado 3)
    10003: quantidade maior (NF 2,  contado 4)
    10004: não encontrado   (NF 1,  sem contagem)
    10005: produto a mais   (fora da NF, contado 2)
    """

    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "10001", 10)
    fabrica.item_nf(conferencia, "10002", 5)
    fabrica.item_nf(conferencia, "10003", 2)
    fabrica.item_nf(conferencia, "10004", 1)

    fabrica.contagem(conferencia, "10001", 10)
    fabrica.contagem(conferencia, "10002", 3)
    fabrica.contagem(conferencia, "10003", 4)
    fabrica.contagem(conferencia, "10005", 2)

    return conferencia


# ============================================================
# CONTRATO
# ============================================================

def test_contrato_da_resposta(client, fabrica, conferente):
    conferencia = cenario_completo(fabrica)

    resposta = client.get(f"/conferencia/{conferencia.id}")

    assert resposta.status_code == 200

    dados = resposta.json()

    assert set(dados) == CHAVES_RESPOSTA
    assert isinstance(dados["status"], str)
    assert isinstance(dados["status_conferencia"], str)
    assert isinstance(dados["total_itens"], int)
    assert isinstance(dados["divergentes"], int)
    assert isinstance(dados["versao"], int)
    assert isinstance(dados["itens"], list)

    for item in dados["itens"]:
        assert set(item) == CHAVES_ITEM
        assert isinstance(item["codigo"], str)
        assert isinstance(item["xml"], (int, float))
        assert isinstance(item["contado"], (int, float))
        assert isinstance(item["diferenca"], (int, float))
        assert isinstance(item["divergente"], bool)
        assert isinstance(item["justificado"], bool)
        assert item["divergencia_id"] is None or isinstance(
            item["divergencia_id"], int
        )


def test_comparacao_tipos_e_totalizadores(client, fabrica, conferente):
    conferencia = cenario_completo(fabrica)

    dados = client.get(f"/conferencia/{conferencia.id}").json()
    itens = itens_por_codigo(dados)

    assert dados["status"] == "divergente"
    assert dados["status_conferencia"] == "RASCUNHO"
    assert dados["versao"] == 1
    assert dados["total_itens"] == 5
    assert dados["divergentes"] == 4

    assert itens["10001"]["divergente"] is False
    assert itens["10001"]["tipo_divergencia"] is None
    assert itens["10001"]["divergencia_id"] is None
    assert itens["10001"]["descricao"] == "Produto 10001"

    esperado = {
        "10002": ("QUANTIDADE_MENOR", 5, 3, -2),
        "10003": ("QUANTIDADE_MAIOR", 2, 4, 2),
        "10004": ("PRODUTO_NAO_ENCONTRADO", 1, 0, -1),
        "10005": ("PRODUTO_A_MAIS", 0, 2, 2),
    }

    for codigo, (tipo, xml, contado, diferenca) in esperado.items():
        item = itens[codigo]

        assert item["divergente"] is True
        assert item["tipo_divergencia"] == tipo
        assert item["xml"] == xml
        assert item["contado"] == contado
        assert item["diferenca"] == diferenca
        assert item["justificado"] is False


def test_sem_divergencia(client, fabrica, conferente):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "20001", 3)
    fabrica.contagem(conferencia, "20001", 3)

    dados = client.get(f"/conferencia/{conferencia.id}").json()

    assert dados["status"] == "ok"
    assert dados["divergentes"] == 0
    assert dados["total_itens"] == 1


def test_consolida_linhas_da_nf_e_normaliza_codigo(
    client, fabrica, conferente
):
    conferencia = fabrica.conferencia()

    # Duas linhas do mesmo produto, uma delas como EAN-13.
    fabrica.item_nf(conferencia, "30001", 3)
    fabrica.item_nf(conferencia, "7890000300011", 2)

    fabrica.contagem(conferencia, "30001", 5)

    dados = client.get(f"/conferencia/{conferencia.id}").json()
    itens = itens_por_codigo(dados)

    assert set(itens) == {"30001"}
    assert itens["30001"]["xml"] == 5
    assert itens["30001"]["divergente"] is False


# ============================================================
# JUSTIFICATIVA E VERSÃO
# ============================================================

def test_exibe_justificativa_da_divergencia_inalterada(
    client, fabrica, conferente
):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "40001", 5)
    fabrica.contagem(conferencia, "40001", 3)

    divergencia = fabrica.divergencia(
        conferencia,
        "40001",
        xml=5,
        contado=3,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Faltou na entrega",
    )

    dados = client.get(f"/conferencia/{conferencia.id}").json()
    item = itens_por_codigo(dados)["40001"]

    assert item["divergencia_id"] == divergencia.id
    assert item["justificado"] is True
    assert item["justificativa_tipo"] == "ERRO_FORNECEDOR"
    assert item["justificativa_descricao"] == "Faltou na entrega"


def test_nao_usa_justificativa_de_versao_anterior(
    client, fabrica, conferente
):
    conferencia = fabrica.conferencia(
        status=StatusConferencia.REABERTA,
        versao=2,
        quantidade_reaberturas=1,
    )

    fabrica.item_nf(conferencia, "50001", 5)
    fabrica.contagem(conferencia, "50001", 3)

    anterior = fabrica.divergencia(
        conferencia,
        "50001",
        xml=5,
        contado=3,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        versao=1,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Justificativa da versão 1",
    )

    dados = client.get(f"/conferencia/{conferencia.id}").json()
    item = itens_por_codigo(dados)["50001"]

    assert dados["versao"] == 2
    assert item["divergente"] is True
    assert item["justificado"] is False
    assert item["justificativa_descricao"] is None
    assert item["divergencia_id"] != anterior.id


# ============================================================
# ACESSO
# ============================================================

def test_conferencia_inexistente(client, conferente):
    resposta = client.get("/conferencia/999")

    assert resposta.status_code == 404


def test_conferente_de_outro_estabelecimento(
    client, fabrica, usuario_atual
):
    usuario_atual.usuario = fabrica.usuario(
        perfil="CONFERENTE",
        estabelecimento_id=2,
    )

    conferencia = fabrica.conferencia(estabelecimento_id=1)

    resposta = client.get(f"/conferencia/{conferencia.id}")

    assert resposta.status_code == 403


def test_auditor_acessa_qualquer_estabelecimento(
    client, fabrica, auditor, usuario_atual
):
    usuario_atual.usuario = auditor

    conferencia = fabrica.conferencia(estabelecimento_id=7)

    resposta = client.get(f"/conferencia/{conferencia.id}")

    assert resposta.status_code == 200
