"""
Autenticação e acesso de POST /notas/importar-xml e GET /itens/.

importar-xml: somente CONFERENTE da loja da conferência.
itens:        regra do GET /conferencia/{id} (auditor: qualquer;
              conferente: própria loja).
"""

import io

import pytest

from app.enums.conferencia_enums import StatusConferencia

from conftest import cabecalho_token


XML = (
    b'<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe>'
    b'<infNFe Id="NFe35260100000000000000550010000000771000000077">'
    b'<ide><nNF>77</nNF></ide><det nItem="1"><prod><cProd>70001</cProd>'
    b'<xProd>Produto</xProd><qCom>4</qCom></prod></det></infNFe></NFe>'
    b'</nfeProc>'
)


@pytest.fixture
def conferente(fabrica):
    return fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=1)


@pytest.fixture
def conferente_outra_loja(fabrica):
    return fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=2)


@pytest.fixture
def auditor(fabrica):
    return fabrica.usuario(perfil="AUDITOR", estabelecimento_id=None)


@pytest.fixture
def conferencia(fabrica):
    return fabrica.conferencia(
        status=StatusConferencia.RASCUNHO,
        estabelecimento_id=1,
    )


def importar(client, conferencia_id, headers=None):
    return client.post(
        "/notas/importar-xml",
        data={"conferencia_id": str(conferencia_id)},
        files={"file": ("nota.xml", io.BytesIO(XML), "text/xml")},
        headers=headers or {},
    )


def itens(client, conferencia_id, headers=None):
    return client.get(
        "/itens/",
        params={"conferencia_id": conferencia_id},
        headers=headers or {},
    )


# ============================================================
# POST /notas/importar-xml
# ============================================================

def test_importar_sem_token_401(client_autenticado, db, conferencia):
    resposta = importar(client_autenticado, conferencia.id)

    assert resposta.status_code == 401


def test_importar_auditor_403(client_autenticado, conferencia, auditor):
    resposta = importar(
        client_autenticado, conferencia.id, cabecalho_token(auditor)
    )

    assert resposta.status_code == 403


def test_importar_conferente_de_outra_loja_403(
    client_autenticado, conferencia, conferente_outra_loja
):
    resposta = importar(
        client_autenticado,
        conferencia.id,
        cabecalho_token(conferente_outra_loja),
    )

    assert resposta.status_code == 403


def test_importar_conferencia_inexistente_404(client_autenticado, conferente):
    resposta = importar(client_autenticado, 999, cabecalho_token(conferente))

    assert resposta.status_code == 404


def test_importar_conferente_da_loja_200(
    client_autenticado, conferencia, conferente
):
    resposta = importar(
        client_autenticado, conferencia.id, cabecalho_token(conferente)
    )

    assert resposta.status_code == 200
    assert resposta.json()["total_itens"] == 1


def test_importacao_recusada_nao_grava_nota(
    client_autenticado, db, conferencia, auditor, conferente_outra_loja
):
    from app.models.item_nf import ItemNF
    from app.models.nota_fiscal import NotaFiscal

    importar(client_autenticado, conferencia.id)
    importar(client_autenticado, conferencia.id, cabecalho_token(auditor))
    importar(
        client_autenticado,
        conferencia.id,
        cabecalho_token(conferente_outra_loja),
    )

    db.expire_all()

    assert db.query(NotaFiscal).count() == 0
    assert db.query(ItemNF).count() == 0


# ============================================================
# GET /itens/
# ============================================================

def test_itens_sem_token_401(client_autenticado, conferencia):
    assert itens(client_autenticado, conferencia.id).status_code == 401


def test_itens_conferente_de_outra_loja_403(
    client_autenticado, conferencia, conferente_outra_loja
):
    resposta = itens(
        client_autenticado,
        conferencia.id,
        cabecalho_token(conferente_outra_loja),
    )

    assert resposta.status_code == 403


def test_itens_conferencia_inexistente_404(client_autenticado, conferente):
    resposta = itens(client_autenticado, 999, cabecalho_token(conferente))

    assert resposta.status_code == 404


def test_itens_conferente_da_loja_200(
    client_autenticado, fabrica, conferencia, conferente
):
    fabrica.item_nf(conferencia, "70002", 3)

    resposta = itens(
        client_autenticado, conferencia.id, cabecalho_token(conferente)
    )

    assert resposta.status_code == 200
    assert [i["codigo"] for i in resposta.json()] == ["70002"]


def test_itens_auditor_200(client_autenticado, fabrica, auditor):
    conferencia = fabrica.conferencia(estabelecimento_id=9)
    fabrica.item_nf(conferencia, "70003", 1)

    resposta = itens(
        client_autenticado, conferencia.id, cabecalho_token(auditor)
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
