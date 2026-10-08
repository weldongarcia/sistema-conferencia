"""
Tabela central de operações permitidas por estado.
"""

from types import SimpleNamespace

import pytest

from fastapi import HTTPException

from app.enums.conferencia_enums import StatusConferencia as S
from app.services.estado_conferencia import (
    ESTADOS_EDITAVEIS,
    ESTADOS_PERMITIDOS,
    MENSAGENS,
    Operacao,
    exigir_operacao_permitida,
    operacao_permitida,
)


ESPERADO = {
    Operacao.CONTAGEM: {S.RASCUNHO, S.REABERTA},
    Operacao.SINCRONIZACAO: {S.RASCUNHO, S.REABERTA},
    Operacao.JUSTIFICAR: {S.RASCUNHO, S.REABERTA},
    Operacao.FECHAR: {S.RASCUNHO, S.REABERTA},
    Operacao.IMPORTAR_XML: {S.RASCUNHO, S.REABERTA},
    Operacao.APROVAR: {S.FINALIZADA},
    Operacao.REPROVAR: {S.FINALIZADA},
    Operacao.REABRIR: {S.FINALIZADA, S.REPROVADA},
}


def test_tabela_cobre_todas_as_operacoes():
    assert set(ESTADOS_PERMITIDOS) == set(Operacao)
    assert set(MENSAGENS) == set(Operacao)


def test_tabela_corresponde_a_regra():
    assert {op: set(estados) for op, estados in ESTADOS_PERMITIDOS.items()} == ESPERADO


def test_somente_rascunho_e_reaberta_sao_editaveis():
    assert ESTADOS_EDITAVEIS == {S.RASCUNHO, S.REABERTA}


@pytest.mark.parametrize("operacao", list(Operacao))
def test_aprovada_nao_permite_nenhuma_operacao(operacao):
    assert not operacao_permitida(S.APROVADA, operacao)


@pytest.mark.parametrize("status", [S.EM_CONFERENCIA, S.EM_AUDITORIA])
@pytest.mark.parametrize("operacao", list(Operacao))
def test_estados_nao_utilizados_nao_permitem_nada(status, operacao):
    assert not operacao_permitida(status, operacao)


def test_reprovada_so_permite_reabrir():
    assert {
        op for op in Operacao if operacao_permitida(S.REPROVADA, op)
    } == {Operacao.REABRIR}


def test_exigir_operacao_permitida_recusa_com_400_e_status():
    conferencia = SimpleNamespace(status=S.APROVADA)

    with pytest.raises(HTTPException) as erro:
        exigir_operacao_permitida(conferencia, Operacao.FECHAR)

    assert erro.value.status_code == 400
    assert erro.value.detail == (
        "Não é possível fechar uma conferência com status APROVADA."
    )


def test_exigir_operacao_permitida_aceita():
    conferencia = SimpleNamespace(status=S.REABERTA)

    assert exigir_operacao_permitida(conferencia, Operacao.CONTAGEM) is None


@pytest.mark.parametrize(
    ("operacao", "mensagem"),
    [
        (Operacao.APROVAR,
         "Somente conferências finalizadas podem ser aprovadas."),
        (Operacao.REPROVAR,
         "Somente conferências finalizadas podem ser reprovadas."),
        (Operacao.REABRIR,
         "Somente conferências finalizadas ou reprovadas "
         "podem ser reabertas."),
    ],
)
def test_mensagens_das_transicoes_do_auditor_preservadas(operacao, mensagem):
    with pytest.raises(HTTPException) as erro:
        exigir_operacao_permitida(
            SimpleNamespace(status=S.RASCUNHO), operacao
        )

    assert erro.value.detail == mensagem


def test_busca_para_alteracao_usa_for_update_no_postgresql(db):
    # O SQLite ignora a trava; a consulta é compilada para o
    # dialeto do PostgreSQL para provar que FOR UPDATE é emitido.
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Query

    from app.services import estado_conferencia

    capturadas = []
    original = Query.first

    def capturar(self):
        capturadas.append(self)
        return original(self)

    Query.first = capturar

    try:
        estado_conferencia.buscar_conferencia_para_alteracao(db, 1)
    finally:
        Query.first = original

    (consulta,) = capturadas

    sql = str(consulta.statement.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE" in sql
    assert "FROM conferencias" in sql
