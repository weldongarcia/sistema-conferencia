"""
Máquina de estados da conferência (BACKEND-02A).

Matriz completa estado x operação pelas rotas HTTP reais, com
autenticação real. A tabela de operações permitidas é definida AQUI,
de forma independente do código de produção.

Quando uma operação é recusada pelo estado, o teste prova que o banco
não mudou (fotografia de todas as tabelas antes e depois).
"""

import io

import pytest

from app.enums.conferencia_enums import (
    StatusConferencia as S,
    TipoDivergencia,
    TipoJustificativa,
)
from app.models.conferencia import Conferencia
from app.models.conferencia_historico import ConferenciaHistorico
from app.models.contagem import Contagem
from app.models.divergencia import Divergencia
from app.models.item_nf import ItemNF
from app.models.nota_fiscal import NotaFiscal

from conftest import cabecalho_token, fotografar_banco


# ============================================================
# REGRA ESPERADA (independente da implementação)
# ============================================================

EDITAVEIS = {S.RASCUNHO, S.REABERTA}

PERMITIDAS = {
    "contagem": EDITAVEIS,
    "sincronizar_conferencias": EDITAVEIS,
    "sincronizar_contagens": EDITAVEIS,
    "justificar": EDITAVEIS,
    "fechar": EDITAVEIS,
    "aprovar": {S.FINALIZADA},
    "reprovar": {S.FINALIZADA},
    "reabrir": {S.FINALIZADA, S.REPROVADA},
    "importar_xml": EDITAVEIS,
}

ESTADOS = [
    S.RASCUNHO,
    S.EM_CONFERENCIA,
    S.FINALIZADA,
    S.EM_AUDITORIA,
    S.APROVADA,
    S.REPROVADA,
    S.REABERTA,
]


# ============================================================
# DADOS
# ============================================================

@pytest.fixture
def conferente(fabrica):
    return fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=1)


@pytest.fixture
def auditor(fabrica):
    return fabrica.usuario(perfil="AUDITOR", estabelecimento_id=None)


def conferencia_em(fabrica, db, status, com_nota=True):
    """
    Conferência no estado pedido, com NF 80001=5, contagem 80001=3 e
    a divergência correspondente da versão atual já justificada.
    Assim, fechar e aprovar só dependem do estado.
    """

    reaberta = status == S.REABERTA

    conferencia = fabrica.conferencia(
        status=status,
        versao=2 if reaberta else 1,
        quantidade_reaberturas=1 if reaberta else 0,
        estabelecimento_id=1,
    )

    if com_nota:
        db.add(NotaFiscal(
            chave_acesso=f"chave-teste-{conferencia.id}",
            numero="1",
            conferencia_id=conferencia.id,
        ))
        db.commit()

        fabrica.item_nf(conferencia, "80001", 5)

    fabrica.contagem(conferencia, "80001", 3)

    divergencia = None

    if com_nota:
        divergencia = fabrica.divergencia(
            conferencia, "80001", xml=5, contado=3,
            tipo=TipoDivergencia.QUANTIDADE_MENOR,
            justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
            justificativa_descricao="Justificativa original",
        )

    return conferencia, divergencia


XML = (
    '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe>'
    '<infNFe Id="NFe35260100000000000000550010000000551000000055">'
    '<ide><nNF>55</nNF></ide><det nItem="1"><prod><cProd>80009</cProd>'
    '<xProd>Produto</xProd><qCom>2</qCom></prod></det></infNFe></NFe>'
    '</nfeProc>'
).encode()


def executar(client, operacao, conferencia, divergencia, conferente, auditor):
    c = conferencia.id

    if operacao == "contagem":
        return client.post(
            "/contagens/", headers=cabecalho_token(conferente),
            json={"conferencia_id": c, "codigo": "80001", "quantidade": 1},
        )

    if operacao == "sincronizar_conferencias":
        return client.post(
            f"/conferencias/{c}/sincronizar",
            headers=cabecalho_token(conferente),
            json={"itens": [{"codigo": "80001", "quantidade": 4}]},
        )

    if operacao == "sincronizar_contagens":
        return client.post(
            f"/contagens/sincronizar/{c}",
            headers=cabecalho_token(conferente),
            json={"itens": [{"codigo": "80001", "quantidade": 2}]},
        )

    if operacao == "justificar":
        return client.post(
            f"/divergencias/{divergencia.id}/justificar",
            headers=cabecalho_token(conferente),
            json={
                "justificativa_tipo": "OUTROS",
                "justificativa_descricao": "Nova justificativa",
            },
        )

    if operacao == "fechar":
        return client.post(
            f"/conferencia/{c}/fechar", headers=cabecalho_token(conferente)
        )

    if operacao == "aprovar":
        return client.post(
            f"/conferencia/{c}/aprovar", headers=cabecalho_token(auditor)
        )

    if operacao == "reprovar":
        return client.post(
            f"/conferencia/{c}/reprovar", headers=cabecalho_token(auditor),
            json="Motivo da reprovação",
        )

    if operacao == "reabrir":
        return client.post(
            f"/conferencia/{c}/reabrir", headers=cabecalho_token(auditor),
            json="Motivo da reabertura",
        )

    if operacao == "importar_xml":
        return client.post(
            "/notas/importar-xml", headers=cabecalho_token(conferente),
            data={"conferencia_id": str(c)},
            files={"file": ("nota.xml", io.BytesIO(XML), "text/xml")},
        )

    raise AssertionError(operacao)


def estado_atual(db, conferencia):
    db.expire_all()
    return db.get(Conferencia, conferencia.id)


def historico(db, conferencia):
    db.expire_all()
    return [
        (h.acao, h.versao, h.motivo)
        for h in db.query(ConferenciaHistorico)
        .filter_by(conferencia_id=conferencia.id)
        .order_by(ConferenciaHistorico.id)
    ]


def contagem_de(db, conferencia, codigo="80001"):
    db.expire_all()
    linha = db.query(Contagem).filter_by(
        conferencia_id=conferencia.id, codigo=codigo
    ).one()
    return linha.quantidade


def verificar_efeito_permitido(db, operacao, conferencia, status, versao):
    atual = estado_atual(db, conferencia)
    eventos = historico(db, conferencia)

    if operacao == "contagem":
        assert atual.status == status
        assert contagem_de(db, conferencia) == 4

    elif operacao == "sincronizar_conferencias":
        assert atual.status == status
        assert contagem_de(db, conferencia) == 4

    elif operacao == "sincronizar_contagens":
        assert atual.status == status
        assert contagem_de(db, conferencia) == 2

    elif operacao == "justificar":
        assert atual.status == status
        db.expire_all()
        linha = db.query(Divergencia).filter_by(
            conferencia_id=conferencia.id, versao=versao
        ).one()
        assert linha.justificativa_descricao == "Nova justificativa"
        assert eventos[-1][0] == "DIVERGENCIA_JUSTIFICADA"

    elif operacao == "fechar":
        assert atual.status == S.FINALIZADA
        assert eventos[-1][:2] == ("FINALIZADA", versao)

    elif operacao == "aprovar":
        assert atual.status == S.APROVADA
        assert eventos[-1][:2] == ("APROVADA", versao)

    elif operacao == "reprovar":
        assert atual.status == S.REPROVADA
        assert eventos[-1] == ("REPROVADA", versao, "Motivo da reprovação")

    elif operacao == "reabrir":
        assert atual.status == S.REABERTA
        assert atual.versao == versao + 1
        assert eventos[-1] == (
            "REABERTA", versao + 1, "Motivo da reabertura"
        )

    elif operacao == "importar_xml":
        assert atual.status == status
        db.expire_all()
        assert db.query(NotaFiscal).filter_by(
            conferencia_id=conferencia.id
        ).count() == 1
        assert [i.codigo for i in db.query(ItemNF).filter_by(
            conferencia_id=conferencia.id
        )] == ["80009"]

    assert atual.versao == (versao + 1 if operacao == "reabrir" else versao)


# ============================================================
# MATRIZ ESTADO x OPERAÇÃO
# ============================================================

def _casos():
    for status in ESTADOS:
        for operacao in PERMITIDAS:
            yield pytest.param(
                status,
                operacao,
                id=f"{status.value}-{operacao}",
            )


@pytest.mark.parametrize(("status", "operacao"), list(_casos()))
def test_matriz_estado_operacao(
    client_autenticado, db, fabrica, conferente, auditor, status, operacao
):
    conferencia, divergencia = conferencia_em(
        fabrica, db, status, com_nota=operacao != "importar_xml"
    )

    if operacao == "justificar":
        assert divergencia is not None

    versao = conferencia.versao
    antes = fotografar_banco(db)

    resposta = executar(
        client_autenticado, operacao, conferencia, divergencia,
        conferente, auditor,
    )

    if status in PERMITIDAS[operacao]:
        assert resposta.status_code == 200, resposta.text
        verificar_efeito_permitido(db, operacao, conferencia, status, versao)
    else:
        assert resposta.status_code == 400, resposta.text
        assert fotografar_banco(db) == antes


# ============================================================
# CENÁRIOS DE FLUXO
# ============================================================

def test_aprovada_e_imutavel(
    client_autenticado, db, fabrica, conferente, auditor
):
    conferencia, divergencia = conferencia_em(fabrica, db, S.APROVADA)

    antes = fotografar_banco(db)

    codigos = [
        executar(client_autenticado, operacao, conferencia, divergencia,
                 conferente, auditor).status_code
        for operacao in PERMITIDAS
        if operacao != "importar_xml"
    ]

    assert codigos == [400] * len(codigos)
    assert fotografar_banco(db) == antes
    assert estado_atual(db, conferencia).status == S.APROVADA


def test_reprovada_exige_reabertura(
    client_autenticado, db, fabrica, conferente, auditor
):
    conferencia, divergencia = conferencia_em(fabrica, db, S.FINALIZADA)

    def chamar(operacao, div=divergencia):
        return executar(client_autenticado, operacao, conferencia, div,
                        conferente, auditor)

    assert chamar("reprovar").status_code == 200

    # O conferente não corrige nem fecha diretamente a reprovada.
    antes = fotografar_banco(db)
    for operacao in ("contagem", "sincronizar_conferencias",
                     "sincronizar_contagens", "justificar", "fechar"):
        assert chamar(operacao).status_code == 400, operacao
    assert fotografar_banco(db) == antes

    assert chamar("reabrir").status_code == 200

    atual = estado_atual(db, conferencia)
    assert (atual.status, atual.versao) == (S.REABERTA, 2)

    # Na versão 2 a contagem volta a ser permitida.
    assert chamar("contagem").status_code == 200  # 80001: 3 -> 4

    db.expire_all()
    nova = db.query(Divergencia).filter_by(
        conferencia_id=conferencia.id, versao=2
    ).one()

    assert chamar("justificar", nova).status_code == 200
    assert chamar("fechar").status_code == 200
    assert chamar("aprovar").status_code == 200

    assert estado_atual(db, conferencia).status == S.APROVADA


def test_finalizada_pode_ser_reaberta_e_finalizada_de_novo(
    client_autenticado, db, fabrica, conferente, auditor
):
    conferencia, divergencia = conferencia_em(fabrica, db, S.FINALIZADA)

    def chamar(operacao, div=divergencia):
        return executar(client_autenticado, operacao, conferencia, div,
                        conferente, auditor)

    assert chamar("reabrir").status_code == 200

    db.expire_all()
    nova = db.query(Divergencia).filter_by(
        conferencia_id=conferencia.id, versao=2
    ).one()

    assert chamar("justificar", nova).status_code == 200
    assert chamar("fechar").status_code == 200

    atual = estado_atual(db, conferencia)
    assert (atual.status, atual.versao) == (S.FINALIZADA, 2)


# ============================================================
# ISOLAMENTO POR LOJA (regra preservada)
# ============================================================

@pytest.mark.parametrize(
    "operacao",
    ["contagem", "sincronizar_conferencias", "sincronizar_contagens",
     "justificar", "fechar", "importar_xml"],
)
def test_conferente_de_outra_loja_recebe_403(
    client_autenticado, db, fabrica, auditor, operacao
):
    outro = fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=2)

    conferencia, divergencia = conferencia_em(
        fabrica, db, S.RASCUNHO, com_nota=operacao != "importar_xml"
    )

    antes = fotografar_banco(db)

    resposta = executar(client_autenticado, operacao, conferencia,
                        divergencia, outro, auditor)

    assert resposta.status_code == 403
    assert fotografar_banco(db) == antes
