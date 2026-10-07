"""
Testes do script de recálculo de divergências legadas
(backend/scripts/recalcular_divergencias.py).
"""

import pytest

from sqlalchemy import event

from app.enums.conferencia_enums import (
    StatusConferencia,
    TipoDivergencia,
    TipoJustificativa,
)
from app.models.divergencia import Divergencia
from app.services import divergencia_service

from scripts import recalcular_divergencias as script

from conftest import fotografar, fotografar_banco


# ============================================================
# AUXILIARES
# ============================================================

def linhas(db, conferencia, versao=None):
    db.expire_all()

    return {
        d.codigo: d
        for d in db.query(Divergencia).filter(
            Divergencia.conferencia_id == conferencia.id,
            Divergencia.versao == (
                versao if versao is not None else conferencia.versao
            ),
        )
    }


def resumo_linhas(db, conferencia, versao=None):
    return {
        codigo: (
            getattr(d.tipo, "value", d.tipo),
            d.xml,
            d.contado,
            d.justificativa_descricao,
        )
        for codigo, d in linhas(db, conferencia, versao).items()
    }


def contar_commits(db):
    commits = []

    def registrar(sessao):
        commits.append(1)

    event.listen(db, "after_commit", registrar)

    return commits, lambda: event.remove(db, "after_commit", registrar)


def conferencia_legada(fabrica, status=StatusConferencia.RASCUNHO):
    """
    40001: ausente       (NF 5, contado 2, nada gravado)       -> criar
    40002: obsoleta      (NF 5, contado 5, gravada 5/2 just.)  -> remover
    40003: mudou         (NF 5, contado 3, gravada 5/2 just.)  -> atualizar
    40004: inalterada    (NF 5, contado 1, gravada 5/1 just.)  -> preservar
    """

    conferencia = fabrica.conferencia(status=status)

    for codigo in ("40001", "40002", "40003", "40004"):
        fabrica.item_nf(conferencia, codigo, 5)

    for codigo, contado in (
        ("40001", 2),
        ("40002", 5),
        ("40003", 3),
        ("40004", 1),
    ):
        fabrica.contagem(conferencia, codigo, contado)

    for codigo, contado in (("40002", 2), ("40003", 2), ("40004", 1)):
        fabrica.divergencia(
            conferencia, codigo, xml=5, contado=contado,
            tipo=TipoDivergencia.QUANTIDADE_MENOR,
            justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
            justificativa_descricao=f"Justificativa {codigo}",
        )

    return conferencia


ESTADO_CORRIGIDO = {
    "40001": ("QUANTIDADE_MENOR", 5, 2, None),
    "40003": ("QUANTIDADE_MENOR", 5, 3, None),
    "40004": ("QUANTIDADE_MENOR", 5, 1, "Justificativa 40004"),
}


# ============================================================
# DRY-RUN
# ============================================================

def test_dry_run_nao_altera_o_banco(db, fabrica):
    conferencia_legada(fabrica)

    antes = fotografar_banco(db)
    commits, remover = contar_commits(db)

    try:
        relatorio = script.executar(db)
    finally:
        remover()

    assert relatorio.aplicado is False
    assert commits == []
    assert fotografar_banco(db) == antes


def test_dry_run_preve_exatamente_o_que_apply_faz(db, fabrica):
    conferencia_legada(fabrica)

    previsto = script.executar(db, aplicar=False)
    aplicado = script.executar(db, aplicar=True)

    campos = (
        "criar",
        "atualizar",
        "remover",
        "justificativas_preservadas",
        "justificativas_invalidadas",
        "justificativas_removidas",
        "total_alteracoes",
    )

    assert {c: getattr(previsto, c) for c in campos} == {
        "criar": 1,
        "atualizar": 1,
        "remover": 1,
        "justificativas_preservadas": 1,
        "justificativas_invalidadas": 1,
        "justificativas_removidas": 1,
        "total_alteracoes": 3,
    }

    assert {c: getattr(aplicado, c) for c in campos} == {
        c: getattr(previsto, c) for c in campos
    }


def test_main_padrao_e_dry_run(SessionTeste, db, fabrica, capsys):
    conferencia_legada(fabrica)

    antes = fotografar_banco(db)

    assert script.main([], sessao_factory=SessionTeste) == 0

    saida = capsys.readouterr().out

    assert "DRY-RUN (nada foi gravado)" in saida
    assert "Total de alterações previstas:" in saida
    assert "--apply" in saida
    assert fotografar_banco(db) == antes


# ============================================================
# APPLY
# ============================================================

@pytest.mark.parametrize(
    "status",
    [StatusConferencia.RASCUNHO, StatusConferencia.REABERTA],
    ids=["RASCUNHO", "REABERTA"],
)
def test_apply_corrige_status_processados(db, fabrica, status):
    conferencia = conferencia_legada(fabrica, status=status)

    relatorio = script.executar(db, aplicar=True)

    assert [r.conferencia_id for r in relatorio.analisadas] == [
        conferencia.id
    ]
    assert relatorio.ignoradas == []
    assert resumo_linhas(db, conferencia) == ESTADO_CORRIGIDO


def test_main_apply(SessionTeste, db, fabrica, capsys):
    conferencia = conferencia_legada(fabrica)

    assert script.main(["--apply"], sessao_factory=SessionTeste) == 0

    saida = capsys.readouterr().out

    assert "APLICADO" in saida
    assert resumo_linhas(db, conferencia) == ESTADO_CORRIGIDO


@pytest.mark.parametrize(
    "status",
    [
        StatusConferencia.FINALIZADA,
        StatusConferencia.APROVADA,
        StatusConferencia.REPROVADA,
        StatusConferencia.EM_CONFERENCIA,
    ],
    ids=["FINALIZADA", "APROVADA", "REPROVADA", "EM_CONFERENCIA"],
)
def test_apply_ignora_outros_status(db, fabrica, status):
    conferencia = conferencia_legada(fabrica, status=status)

    antes = fotografar_banco(db)

    relatorio = script.executar(db, aplicar=True)

    assert relatorio.analisadas == []
    assert relatorio.ignoradas == [(conferencia.id, status.value)]
    assert relatorio.total_alteracoes == 0
    assert fotografar_banco(db) == antes


def test_processa_apenas_os_status_permitidos_numa_base_mista(db, fabrica):
    rascunho = conferencia_legada(fabrica)
    aprovada = conferencia_legada(
        fabrica, status=StatusConferencia.APROVADA
    )

    aprovada_antes = fotografar(
        db, Divergencia, Divergencia.conferencia_id == aprovada.id
    )

    script.executar(db, aplicar=True)

    assert resumo_linhas(db, rascunho) == ESTADO_CORRIGIDO
    assert fotografar(
        db, Divergencia, Divergencia.conferencia_id == aprovada.id
    ) == aprovada_antes


def test_filtro_por_conferencia(db, fabrica):
    primeira = conferencia_legada(fabrica)
    segunda = conferencia_legada(fabrica)

    segunda_antes = fotografar(
        db, Divergencia, Divergencia.conferencia_id == segunda.id
    )

    relatorio = script.executar(
        db, aplicar=True, conferencia_ids=[primeira.id]
    )

    assert [r.conferencia_id for r in relatorio.analisadas] == [
        primeira.id
    ]
    assert resumo_linhas(db, primeira) == ESTADO_CORRIGIDO
    assert fotografar(
        db, Divergencia, Divergencia.conferencia_id == segunda.id
    ) == segunda_antes


# ============================================================
# CASOS INDIVIDUAIS
# ============================================================

def test_cria_divergencia_ausente(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "41001", 5)

    relatorio = script.executar(db, aplicar=True)

    assert relatorio.criar == 1
    assert resumo_linhas(db, conferencia) == {
        "41001": ("PRODUTO_NAO_ENCONTRADO", 5, 0, None),
    }


def test_remove_divergencia_obsoleta(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "41002", 5)
    fabrica.contagem(conferencia, "41002", 5)

    fabrica.divergencia(
        conferencia, "41002", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
    )

    relatorio = script.executar(db, aplicar=True)

    assert relatorio.remover == 1
    assert relatorio.justificativas_removidas == 0
    assert linhas(db, conferencia) == {}


def test_preserva_justificativa_sem_mudanca_material(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "41003", 5)
    fabrica.contagem(conferencia, "41003", 2)

    fabrica.divergencia(
        conferencia, "41003", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Mantida",
    )

    relatorio = script.executar(db, aplicar=True)

    assert relatorio.justificativas_preservadas == 1
    assert relatorio.justificativas_invalidadas == 0
    assert relatorio.total_alteracoes == 0
    assert linhas(db, conferencia)["41003"].justificativa_descricao == (
        "Mantida"
    )


def test_invalida_justificativa_com_mudanca_material(db, fabrica):
    # Gravada como QUANTIDADE_MENOR pelo sync antigo; pela regra
    # única, contagem 0 é PRODUTO_NAO_ENCONTRADO.
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "41004", 5)
    fabrica.contagem(conferencia, "41004", 0)

    fabrica.divergencia(
        conferencia, "41004", xml=5, contado=0,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Tipo antigo",
    )

    relatorio = script.executar(db, aplicar=True)

    assert relatorio.atualizar == 1
    assert relatorio.justificativas_invalidadas == 1
    assert resumo_linhas(db, conferencia) == {
        "41004": ("PRODUTO_NAO_ENCONTRADO", 5, 0, None),
    }


def test_nao_altera_versao_anterior(db, fabrica):
    conferencia = fabrica.conferencia(
        status=StatusConferencia.REABERTA,
        versao=2,
        quantidade_reaberturas=1,
    )

    fabrica.item_nf(conferencia, "41005", 5)
    fabrica.contagem(conferencia, "41005", 5)

    fabrica.divergencia(
        conferencia, "41005", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        versao=1,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Versão 1",
    )

    filtro_v1 = (
        Divergencia.conferencia_id == conferencia.id,
        Divergencia.versao == 1,
    )
    v1_antes = fotografar(db, Divergencia, *filtro_v1)

    script.executar(db, aplicar=True)

    assert fotografar(db, Divergencia, *filtro_v1) == v1_antes


# ============================================================
# IDEMPOTÊNCIA
# ============================================================

def test_execucao_repetida_e_idempotente(db, fabrica):
    conferencia_legada(fabrica)
    conferencia_legada(fabrica, status=StatusConferencia.REABERTA)

    primeira = script.executar(db, aplicar=True)
    depois_da_primeira = fotografar_banco(db)

    segunda = script.executar(db, aplicar=True)

    assert primeira.total_alteracoes == 6
    assert segunda.total_alteracoes == 0
    assert segunda.justificativas_invalidadas == 0
    assert fotografar_banco(db) == depois_da_primeira


# ============================================================
# ROLLBACK
# ============================================================

def falhar_na_segunda_conferencia(monkeypatch):
    chamadas = []
    original = divergencia_service.recalcular_divergencias

    def recalcular_com_falha(db, conferencia):
        chamadas.append(conferencia.id)

        if len(chamadas) == 2:
            raise RuntimeError("falha simulada")

        return original(db, conferencia)

    monkeypatch.setattr(script, "recalcular_divergencias", recalcular_com_falha)

    return chamadas


def test_erro_nao_deixa_alteracoes_parciais(db, fabrica, monkeypatch):
    conferencia_legada(fabrica)
    conferencia_legada(fabrica)

    antes = fotografar_banco(db)

    chamadas = falhar_na_segunda_conferencia(monkeypatch)

    with pytest.raises(RuntimeError, match="falha simulada"):
        script.executar(db, aplicar=True)

    # A primeira conferência foi recalculada antes da falha,
    # mas nada foi mantido.
    assert len(chamadas) == 2
    assert fotografar_banco(db) == antes


def test_main_retorna_erro_sem_gravar(
    SessionTeste, db, fabrica, monkeypatch, capsys
):
    conferencia_legada(fabrica)
    conferencia_legada(fabrica)

    antes = fotografar_banco(db)

    falhar_na_segunda_conferencia(monkeypatch)

    codigo = script.main(["--apply"], sessao_factory=SessionTeste)

    erro = capsys.readouterr().err

    assert codigo == 1
    assert "nenhuma alteração foi gravada" in erro
    assert fotografar_banco(db) == antes
