"""
Testes de recalcular_divergencias.

O serviço não faz commit; os testes fazem o commit no lugar
do fluxo chamador quando precisam verificar o estado gravado.
"""

import pytest

from sqlalchemy import event

from app.enums.conferencia_enums import (
    StatusConferencia,
    TipoDivergencia,
    TipoJustificativa,
)
from app.models.divergencia import Divergencia
from app.services.divergencia_service import recalcular_divergencias

from conftest import fotografar, fotografar_banco


def divergencias_da_versao(db, conferencia, versao=None):
    db.expire_all()

    return {
        d.codigo: d
        for d in (
            db.query(Divergencia)
            .filter(
                Divergencia.conferencia_id == conferencia.id,
                Divergencia.versao == (
                    versao if versao is not None else conferencia.versao
                ),
            )
            .all()
        )
    }


def recalcular(db, conferencia):
    resumo = recalcular_divergencias(db, conferencia)
    db.commit()
    return resumo


def justificar(divergencia, descricao="Justificada"):
    divergencia.justificativa_tipo = TipoJustificativa.ERRO_FORNECEDOR
    divergencia.justificativa_descricao = descricao


# ============================================================
# REGRA ÚNICA PERSISTIDA
# ============================================================

def test_cria_divergencias_segundo_a_regra_unica(db, fabrica):
    conferencia = fabrica.conferencia()

    # NF sem contagem / NF com contagem 0 / menor / igual / maior
    fabrica.item_nf(conferencia, "10001", 5)
    fabrica.item_nf(conferencia, "10002", 5)
    fabrica.item_nf(conferencia, "10003", 5)
    fabrica.item_nf(conferencia, "10004", 5)
    fabrica.item_nf(conferencia, "10005", 5)

    fabrica.contagem(conferencia, "10002", 0)
    fabrica.contagem(conferencia, "10003", 2)
    fabrica.contagem(conferencia, "10004", 5)
    fabrica.contagem(conferencia, "10005", 8)

    # Fora da NF: contagem > 0 / contagem 0
    fabrica.contagem(conferencia, "10006", 3)
    fabrica.contagem(conferencia, "10007", 0)

    resumo = recalcular(db, conferencia)

    gravadas = divergencias_da_versao(db, conferencia)

    assert resumo.criadas == 5
    assert {c: (d.tipo, d.origem, d.xml, d.contado, d.diferenca)
            for c, d in gravadas.items()} == {
        "10001": (TipoDivergencia.PRODUTO_NAO_ENCONTRADO, "NOTA", 5, 0, -5),
        "10002": (TipoDivergencia.PRODUTO_NAO_ENCONTRADO, "NOTA", 5, 0, -5),
        "10003": (TipoDivergencia.QUANTIDADE_MENOR, "NOTA", 5, 2, -3),
        "10005": (TipoDivergencia.QUANTIDADE_MAIOR, "NOTA", 5, 8, 3),
        "10006": (TipoDivergencia.PRODUTO_A_MAIS, "FORA_NOTA", 0, 3, 3),
    }

    for divergencia in gravadas.values():
        assert divergencia.versao == conferencia.versao
        assert divergencia.justificativa_tipo is None


def test_idempotente(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "11001", 5)
    fabrica.contagem(conferencia, "11001", 2)
    fabrica.contagem(conferencia, "11002", 1)

    recalcular(db, conferencia)
    antes = fotografar(db, Divergencia)

    resumo = recalcular(db, conferencia)

    assert resumo.houve_alteracao is False
    assert resumo.justificativas_invalidadas == 0
    assert fotografar(db, Divergencia) == antes


# ============================================================
# REMOÇÃO
# ============================================================

def test_remove_divergencia_que_zerou(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "12001", 5)
    contagem = fabrica.contagem(conferencia, "12001", 2)

    recalcular(db, conferencia)

    contagem.quantidade = 5
    db.commit()

    resumo = recalcular(db, conferencia)

    assert resumo.removidas == 1
    assert divergencias_da_versao(db, conferencia) == {}


def test_remove_produto_a_mais_quando_contagem_volta_a_zero(db, fabrica):
    conferencia = fabrica.conferencia()

    contagem = fabrica.contagem(conferencia, "12002", 3)

    recalcular(db, conferencia)
    assert set(divergencias_da_versao(db, conferencia)) == {"12002"}

    contagem.quantidade = 0
    db.commit()

    resumo = recalcular(db, conferencia)

    assert resumo.removidas == 1
    assert divergencias_da_versao(db, conferencia) == {}


def test_remove_divergencias_duplicadas_mantendo_a_justificada(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "12003", 5)
    fabrica.contagem(conferencia, "12003", 2)

    fabrica.divergencia(
        conferencia, "12003", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
    )
    justificada = fabrica.divergencia(
        conferencia, "12003", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Mantida",
    )

    resumo = recalcular(db, conferencia)

    gravadas = divergencias_da_versao(db, conferencia)

    assert resumo.duplicadas_removidas == 1
    assert gravadas["12003"].id == justificada.id
    assert gravadas["12003"].justificativa_descricao == "Mantida"


# ============================================================
# JUSTIFICATIVA
# ============================================================

def test_preserva_justificativa_quando_nada_mudou(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "13001", 5)
    fabrica.contagem(conferencia, "13001", 2)

    recalcular(db, conferencia)

    divergencia = divergencias_da_versao(db, conferencia)["13001"]
    justificar(divergencia, "Faltou na entrega")
    db.commit()

    resumo = recalcular(db, conferencia)

    divergencia = divergencias_da_versao(db, conferencia)["13001"]

    assert resumo.justificativas_invalidadas == 0
    assert divergencia.justificativa_tipo == TipoJustificativa.ERRO_FORNECEDOR
    assert divergencia.justificativa_descricao == "Faltou na entrega"


def test_invalida_justificativa_quando_quantidade_muda(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "13002", 5)
    contagem = fabrica.contagem(conferencia, "13002", 2)

    recalcular(db, conferencia)

    divergencia = divergencias_da_versao(db, conferencia)["13002"]
    id_original = divergencia.id
    justificar(divergencia)
    db.commit()

    contagem.quantidade = 3
    db.commit()

    resumo = recalcular(db, conferencia)

    divergencia = divergencias_da_versao(db, conferencia)["13002"]

    assert resumo.atualizadas == 1
    assert resumo.justificativas_invalidadas == 1
    assert divergencia.id == id_original
    assert divergencia.contado == 3
    assert divergencia.diferenca == -2
    assert divergencia.justificativa_tipo is None
    assert divergencia.justificativa_descricao is None


def test_quantidade_menor_para_nao_encontrado_invalida_justificativa(
    db, fabrica
):
    # Divergência gravada pelo sync antigo como QUANTIDADE_MENOR
    # para um item zerado no snapshot.
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "13003", 5)
    fabrica.contagem(conferencia, "13003", 0)

    fabrica.divergencia(
        conferencia, "13003", xml=5, contado=0,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Justificativa do tipo antigo",
    )

    resumo = recalcular(db, conferencia)

    divergencia = divergencias_da_versao(db, conferencia)["13003"]

    assert resumo.justificativas_invalidadas == 1
    assert divergencia.tipo == TipoDivergencia.PRODUTO_NAO_ENCONTRADO
    assert divergencia.justificativa_tipo is None
    assert divergencia.justificativa_descricao is None


def test_quantidade_fracionada_nao_invalida_justificativa_a_cada_recalculo(
    db, fabrica
):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "13004", "1.5")
    fabrica.contagem(conferencia, "13004", 1)

    recalcular(db, conferencia)

    divergencia = divergencias_da_versao(db, conferencia)["13004"]
    justificar(divergencia)
    db.commit()

    resumo = recalcular(db, conferencia)

    divergencia = divergencias_da_versao(db, conferencia)["13004"]

    assert resumo.houve_alteracao is False
    assert divergencia.justificativa_tipo is not None


# ============================================================
# VERSÕES ANTERIORES
# ============================================================

def criar_conferencia_reaberta_com_historico(fabrica):
    """
    Versão 2 (REABERTA) com linhas da versão 1 que caem nos
    caminhos destrutivos do sync antigo:

    14001: v1 justificada com os mesmos valores atuais
    14002: v1 cuja diferença agora é zero
    14003: v1 com valores diferentes dos atuais
    """

    conferencia = fabrica.conferencia(
        status=StatusConferencia.REABERTA,
        versao=2,
        quantidade_reaberturas=1,
    )

    fabrica.item_nf(conferencia, "14001", 5)
    fabrica.item_nf(conferencia, "14002", 5)
    fabrica.item_nf(conferencia, "14003", 5)

    fabrica.contagem(conferencia, "14001", 2)
    fabrica.contagem(conferencia, "14002", 5)
    fabrica.contagem(conferencia, "14003", 1)

    for codigo, contado in (("14001", 2), ("14002", 3), ("14003", 4)):
        fabrica.divergencia(
            conferencia, codigo, xml=5, contado=contado,
            tipo=TipoDivergencia.QUANTIDADE_MENOR,
            versao=1,
            justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
            justificativa_descricao=f"Justificativa v1 {codigo}",
        )

    return conferencia


def test_nao_altera_versoes_anteriores(db, fabrica):
    conferencia = criar_conferencia_reaberta_com_historico(fabrica)

    filtro_v1 = (
        Divergencia.conferencia_id == conferencia.id,
        Divergencia.versao == 1,
    )

    versao_1_antes = fotografar(db, Divergencia, *filtro_v1)

    recalcular(db, conferencia)

    assert fotografar(db, Divergencia, *filtro_v1) == versao_1_antes

    versao_2 = divergencias_da_versao(db, conferencia, versao=2)

    # 14002 não diverge na v2; 14001 e 14003 nascem sem herdar
    # a justificativa da v1.
    assert set(versao_2) == {"14001", "14003"}

    for divergencia in versao_2.values():
        assert divergencia.justificativa_tipo is None
        assert divergencia.justificativa_descricao is None


# ============================================================
# STATUS NÃO RECALCULÁVEIS
# ============================================================

@pytest.mark.parametrize(
    "status",
    [
        StatusConferencia.FINALIZADA,
        StatusConferencia.APROVADA,
        StatusConferencia.REPROVADA,
    ],
)
def test_nao_grava_em_versao_finalizada_ou_auditada(db, fabrica, status):
    conferencia = fabrica.conferencia(status=status)

    fabrica.item_nf(conferencia, "15001", 5)
    fabrica.item_nf(conferencia, "15002", 5)
    fabrica.contagem(conferencia, "15001", 2)
    fabrica.contagem(conferencia, "15002", 5)

    # Divergência obsoleta e justificada: o recálculo a apagaria
    # ou invalidaria se gravasse.
    fabrica.divergencia(
        conferencia, "15002", xml=5, contado=3,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Auditada",
    )

    antes = fotografar_banco(db)

    resumo = recalcular(db, conferencia)

    assert resumo.ignorado is True
    assert resumo.houve_alteracao is False
    assert fotografar_banco(db) == antes


@pytest.mark.parametrize(
    "status",
    [
        StatusConferencia.RASCUNHO,
        StatusConferencia.EM_CONFERENCIA,
        StatusConferencia.REABERTA,
    ],
)
def test_grava_em_status_editaveis(db, fabrica, status):
    conferencia = fabrica.conferencia(status=status)

    fabrica.item_nf(conferencia, "15003", 5)

    resumo = recalcular(db, conferencia)

    assert resumo.ignorado is False
    assert resumo.criadas == 1


# ============================================================
# TRANSAÇÃO
# ============================================================

def test_nao_faz_commit(db, fabrica):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "16001", 5)

    commits = []

    def registrar_commit(sessao):
        commits.append(1)

    event.listen(db, "after_commit", registrar_commit)

    try:
        resumo = recalcular_divergencias(db, conferencia)

        assert resumo.criadas == 1
        assert commits == []

        # O flush deixa o resultado visível na mesma sessão...
        assert (
            db.query(Divergencia)
            .filter(Divergencia.conferencia_id == conferencia.id)
            .count()
        ) == 1

        # ...mas o chamador decide: rollback descarta tudo.
        db.rollback()

        assert (
            db.query(Divergencia)
            .filter(Divergencia.conferencia_id == conferencia.id)
            .count()
        ) == 0

    finally:
        event.remove(db, "after_commit", registrar_commit)
