"""
Transições da conferência (BACKEND-02A): aprovação com recálculo,
reprovação com motivo obrigatório, atomicidade do histórico e trava
da linha da conferência.

Testes marcados como xfail(strict=True) registram o comportamento
anterior às correções e são liberados à medida que elas entram.
"""

import pytest

from sqlalchemy import event
from sqlalchemy.orm import Query

from app.enums.conferencia_enums import (
    StatusConferencia as S,
    TipoDivergencia,
    TipoJustificativa,
)
from app.models.conferencia import Conferencia
from app.models.conferencia_historico import ConferenciaHistorico
from app.models.contagem import Contagem
from app.models.divergencia import Divergencia
from app.services import conferencia_service
from app.services.conferencia_historico_service import registrar_historico

from conftest import cabecalho_token, fotografar_banco

from test_maquina_estados import (
    PERMITIDAS,
    conferencia_em,
    executar,
)


@pytest.fixture
def conferente(fabrica):
    return fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=1)


@pytest.fixture
def auditor(fabrica):
    return fabrica.usuario(perfil="AUDITOR", estabelecimento_id=None)


def aprovar(client, conferencia, auditor):
    return client.post(
        f"/conferencia/{conferencia.id}/aprovar",
        headers=cabecalho_token(auditor),
    )


def status_de(db, conferencia):
    db.expire_all()
    return db.get(Conferencia, conferencia.id).status


# ============================================================
# APROVAÇÃO RECALCULA ANTES DE VALIDAR
# ============================================================

@pytest.mark.xfail(strict=True, reason="aprovação usava divergências gravadas")
def test_aprovacao_recusa_divergencia_justificada_desatualizada(
    client_autenticado, db, fabrica, auditor
):
    # Justificada para 5/3, mas a contagem real é 2.
    conferencia = fabrica.conferencia(status=S.FINALIZADA)
    fabrica.item_nf(conferencia, "81001", 5)
    contagem = fabrica.contagem(conferencia, "81001", 3)
    fabrica.divergencia(
        conferencia, "81001", xml=5, contado=3,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Justificada para 3",
    )

    contagem.quantidade = 2
    db.commit()

    antes = fotografar_banco(db)

    resposta = aprovar(client_autenticado, conferencia, auditor)

    assert resposta.status_code == 400
    assert "sem justificativa" in resposta.json()["detail"]
    assert fotografar_banco(db) == antes
    assert status_de(db, conferencia) == S.FINALIZADA


@pytest.mark.xfail(strict=True, reason="aprovação usava divergências gravadas")
def test_aprovacao_recusa_divergencia_nao_registrada(
    client_autenticado, db, fabrica, auditor
):
    # Cenário do diagnóstico: contado 9 x NF 2, sem divergência gravada.
    conferencia = fabrica.conferencia(status=S.FINALIZADA)
    fabrica.item_nf(conferencia, "81002", 2)
    fabrica.contagem(conferencia, "81002", 9)

    antes = fotografar_banco(db)

    resposta = aprovar(client_autenticado, conferencia, auditor)

    assert resposta.status_code == 400
    assert fotografar_banco(db) == antes
    assert status_de(db, conferencia) == S.FINALIZADA


@pytest.mark.xfail(strict=True, reason="aprovação usava divergências gravadas")
def test_aprovacao_descarta_divergencia_obsoleta(
    client_autenticado, db, fabrica, auditor
):
    # Pendência gravada para 5/2, mas a contagem real confere (5).
    conferencia = fabrica.conferencia(status=S.FINALIZADA)
    fabrica.item_nf(conferencia, "81003", 5)
    fabrica.contagem(conferencia, "81003", 5)
    fabrica.divergencia(
        conferencia, "81003", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
    )

    resposta = aprovar(client_autenticado, conferencia, auditor)

    assert resposta.status_code == 200
    assert status_de(db, conferencia) == S.APROVADA
    assert db.query(Divergencia).filter_by(
        conferencia_id=conferencia.id
    ).count() == 0


def test_aprovacao_com_divergencias_justificadas_e_correspondentes(
    client_autenticado, db, fabrica, auditor
):
    conferencia = fabrica.conferencia(status=S.FINALIZADA)
    fabrica.item_nf(conferencia, "81004", 5)
    fabrica.contagem(conferencia, "81004", 3)
    fabrica.divergencia(
        conferencia, "81004", xml=5, contado=3,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Faltou na entrega",
    )

    resposta = aprovar(client_autenticado, conferencia, auditor)

    assert resposta.status_code == 200
    assert status_de(db, conferencia) == S.APROVADA

    db.expire_all()
    divergencia = db.query(Divergencia).filter_by(
        conferencia_id=conferencia.id
    ).one()
    assert divergencia.justificativa_descricao == "Faltou na entrega"


# ============================================================
# REPROVAÇÃO COM MOTIVO OBRIGATÓRIO
# ============================================================

def reprovar(client, conferencia, auditor, **kwargs):
    return client.post(
        f"/conferencia/{conferencia.id}/reprovar",
        headers=cabecalho_token(auditor),
        **kwargs,
    )


@pytest.mark.xfail(strict=True, reason="motivo era opcional")
@pytest.mark.parametrize(
    "corpo",
    [{}, {"json": ""}, {"json": "   "}, {"json": None}],
    ids=["sem_corpo", "vazio", "espacos", "null"],
)
def test_reprovacao_exige_motivo(
    client_autenticado, db, fabrica, auditor, corpo
):
    conferencia, _ = conferencia_em(fabrica, db, S.FINALIZADA)

    antes = fotografar_banco(db)

    resposta = reprovar(client_autenticado, conferencia, auditor, **corpo)

    assert resposta.status_code == 400
    assert "motivo" in resposta.json()["detail"].lower()
    assert fotografar_banco(db) == antes


def test_reprovacao_grava_motivo_sem_espacos(
    client_autenticado, db, fabrica, auditor
):
    conferencia, _ = conferencia_em(fabrica, db, S.FINALIZADA)

    resposta = reprovar(
        client_autenticado, conferencia, auditor,
        json="  Recontar a doca 2  ",
    )

    assert resposta.status_code == 200
    assert status_de(db, conferencia) == S.REPROVADA

    evento = db.query(ConferenciaHistorico).filter_by(
        conferencia_id=conferencia.id, acao="REPROVADA"
    ).one()
    assert (evento.versao, evento.motivo) == (1, "Recontar a doca 2")


# ============================================================
# HISTÓRICO E ATOMICIDADE
# ============================================================

@pytest.mark.xfail(strict=True, reason="registrar_historico fazia commit")
def test_registrar_historico_nao_faz_commit(db, fabrica):
    usuario = fabrica.usuario()
    conferencia = fabrica.conferencia()

    commits = []

    def registrar(sessao):
        commits.append(1)

    event.listen(db, "after_commit", registrar)

    try:
        registrar_historico(
            db=db,
            conferencia_id=conferencia.id,
            usuario_id=usuario.id,
            acao="TESTE",
            versao=1,
        )

        assert commits == []
    finally:
        event.remove(db, "after_commit", registrar)
        db.rollback()

    assert db.query(ConferenciaHistorico).count() == 0


def _conferencia_para(transicao, fabrica, db):
    estado = {
        "fechar": S.RASCUNHO,
        "aprovar": S.FINALIZADA,
        "reabrir": S.FINALIZADA,
    }[transicao]

    conferencia, _ = conferencia_em(fabrica, db, estado)
    return conferencia, estado


def _chamar_service(transicao, db, conferencia, usuario):
    if transicao == "fechar":
        return conferencia_service.fechar_conferencia(
            db=db, conferencia_id=conferencia.id, usuario_id=usuario.id
        )

    if transicao == "aprovar":
        return conferencia_service.aprovar_conferencia(
            db=db, conferencia_id=conferencia.id, usuario_id=usuario.id
        )

    if transicao == "reabrir":
        return conferencia_service.reabrir_conferencia(
            db=db, conferencia_id=conferencia.id, usuario_id=usuario.id,
            motivo="Teste de atomicidade",
        )

    raise AssertionError(transicao)


@pytest.mark.xfail(strict=True, reason="histórico era confirmado à parte")
@pytest.mark.parametrize("transicao", ["fechar", "aprovar", "reabrir"])
def test_falha_depois_do_historico_desfaz_toda_a_transicao(
    db, fabrica, monkeypatch, transicao
):
    usuario = fabrica.usuario()
    conferencia, estado = _conferencia_para(transicao, fabrica, db)

    antes = fotografar_banco(db)

    original = conferencia_service.registrar_historico

    def registrar_e_falhar(**kwargs):
        original(**kwargs)
        raise RuntimeError("falha simulada depois do histórico")

    monkeypatch.setattr(
        conferencia_service, "registrar_historico", registrar_e_falhar
    )

    with pytest.raises(RuntimeError):
        _chamar_service(transicao, db, conferencia, usuario)

    # Fim da requisição: a sessão é descartada sem commit.
    db.rollback()

    assert fotografar_banco(db) == antes
    assert status_de(db, conferencia) == estado


# ============================================================
# TRAVA DA LINHA DA CONFERÊNCIA
#
# O SQLite ignora FOR UPDATE; aqui se prova apenas que a consulta
# da conferência é feita com with_for_update(). O efeito real da
# trava só pode ser validado no PostgreSQL.
# ============================================================

ESTADO_PERMITIDO = {
    "contagem": S.RASCUNHO,
    "sincronizar_conferencias": S.RASCUNHO,
    "sincronizar_contagens": S.RASCUNHO,
    "justificar": S.RASCUNHO,
    "fechar": S.RASCUNHO,
    "aprovar": S.FINALIZADA,
    "reprovar": S.FINALIZADA,
    "reabrir": S.FINALIZADA,
    "importar_xml": S.RASCUNHO,
}


@pytest.mark.xfail(strict=True, reason="sem trava antes do BACKEND-02A")
@pytest.mark.parametrize("operacao", list(PERMITIDAS))
def test_operacao_trava_a_linha_da_conferencia(
    client_autenticado, db, fabrica, conferente, auditor, monkeypatch,
    operacao
):
    conferencia, divergencia = conferencia_em(
        fabrica, db, ESTADO_PERMITIDO[operacao],
        com_nota=operacao != "importar_xml",
    )

    travadas = []
    original = Query.with_for_update

    def espiao(self, *args, **kwargs):
        entidades = [d.get("entity") for d in self.column_descriptions]
        travadas.extend(entidades)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Query, "with_for_update", espiao)

    resposta = executar(client_autenticado, operacao, conferencia,
                        divergencia, conferente, auditor)

    assert resposta.status_code == 200, resposta.text
    assert Conferencia in travadas


# ============================================================
# TEXTO DO HISTÓRICO DA JUSTIFICATIVA
# ============================================================

@pytest.mark.xfail(strict=True, reason="gravava TipoJustificativa.X")
def test_historico_da_justificativa_grava_valor_do_tipo(
    client_autenticado, db, fabrica, conferente, auditor
):
    conferencia, divergencia = conferencia_em(fabrica, db, S.RASCUNHO)

    resposta = executar(client_autenticado, "justificar", conferencia,
                        divergencia, conferente, auditor)

    assert resposta.status_code == 200

    evento = db.query(ConferenciaHistorico).filter_by(
        conferencia_id=conferencia.id, acao="DIVERGENCIA_JUSTIFICADA"
    ).one()

    assert evento.motivo == (
        "Produto 80001 | Tipo: OUTROS | Nova justificativa"
    )
