"""
Testes da regra pura de comparação NF x contagem.

calcular_comparacao não acessa o banco; os registros são
simulados com objetos simples.
"""

from types import SimpleNamespace

import pytest

from fastapi import HTTPException

from app.enums.conferencia_enums import TipoDivergencia
from app.services.divergencia_service import calcular_comparacao


def nf(codigo, quantidade, descricao=None):
    # ItemNF.quantidade é String no banco.
    return SimpleNamespace(
        codigo=codigo,
        quantidade=str(quantidade),
        descricao=descricao,
    )


def cont(codigo, quantidade):
    return SimpleNamespace(codigo=codigo, quantidade=quantidade)


def por_codigo(resultado):
    return {item.codigo: item for item in resultado}


def test_sem_divergencia():
    resultado = calcular_comparacao(
        [nf("10001", 10, "Arroz")],
        [cont("10001", 10)],
    )

    item = por_codigo(resultado)["10001"]

    assert item.divergente is False
    assert item.tipo is None
    assert item.origem is None
    assert item.xml == 10
    assert item.contado == 10
    assert item.diferenca == 0
    assert item.descricao == "Arroz"


@pytest.mark.parametrize(
    ("itens_nf", "contagens", "tipo", "origem", "xml", "contado"),
    [
        ([nf("10002", 5)], [cont("10002", 3)],
         TipoDivergencia.QUANTIDADE_MENOR, "NOTA", 5, 3),
        ([nf("10003", 2)], [cont("10003", 4)],
         TipoDivergencia.QUANTIDADE_MAIOR, "NOTA", 2, 4),
        ([nf("10004", 1)], [],
         TipoDivergencia.PRODUTO_NAO_ENCONTRADO, "NOTA", 1, 0),
        ([], [cont("10005", 2)],
         TipoDivergencia.PRODUTO_A_MAIS, "FORA_NOTA", 0, 2),
    ],
)
def test_tipos_de_divergencia(
    itens_nf, contagens, tipo, origem, xml, contado
):
    (item,) = calcular_comparacao(itens_nf, contagens)

    assert item.divergente is True
    assert item.tipo == tipo
    assert item.origem == origem
    assert item.xml == xml
    assert item.contado == contado
    assert item.diferenca == contado - xml


def test_consolida_linhas_repetidas_da_nf():
    resultado = calcular_comparacao(
        [
            nf("20001", 3, "Primeira descrição"),
            nf("20001", 7, "Segunda descrição"),
        ],
        [cont("20001", 10)],
    )

    (item,) = resultado

    assert item.xml == 10
    assert item.divergente is False
    assert item.descricao == "Primeira descrição"


def test_consolida_contagens_repetidas():
    (item,) = calcular_comparacao(
        [nf("20002", 5)],
        [cont("20002", 2), cont("20002", 3)],
    )

    assert item.contado == 5
    assert item.divergente is False


def test_normaliza_ean13_para_codigo_reduzido():
    resultado = calcular_comparacao(
        [nf("7890000300011", 2)],
        [cont("30001", 2)],
    )

    assert [item.codigo for item in resultado] == ["30001"]
    assert resultado[0].divergente is False


def test_codigo_invalido_e_rejeitado():
    with pytest.raises(HTTPException):
        calcular_comparacao([nf("ABC", 1)], [])


def test_resultado_ordenado_por_codigo():
    resultado = calcular_comparacao(
        [nf("30003", 1), nf("30001", 1)],
        [cont("30002", 1)],
    )

    assert [item.codigo for item in resultado] == [
        "30001",
        "30002",
        "30003",
    ]


def test_sem_dados():
    assert calcular_comparacao([], []) == []


# ============================================================
# COMPORTAMENTO ATUAL EM CASOS DE BORDA
#
# Registram a regra herdada do GET. Ver relatório do commit 2
# sobre contagem zero.
# ============================================================

def test_atual_item_da_nf_com_contagem_zero_e_quantidade_menor():
    (item,) = calcular_comparacao(
        [nf("40001", 5)],
        [cont("40001", 0)],
    )

    assert item.tipo == TipoDivergencia.QUANTIDADE_MENOR


def test_atual_produto_fora_da_nf_com_contagem_zero_e_divergente():
    (item,) = calcular_comparacao(
        [],
        [cont("40002", 0)],
    )

    assert item.tipo == TipoDivergencia.PRODUTO_A_MAIS
    assert item.diferenca == 0


def test_atual_quantidade_fracionada_mantida_como_float():
    (item,) = calcular_comparacao(
        [nf("40003", "1.5")],
        [cont("40003", 1)],
    )

    assert item.xml == 1.5
    assert item.diferenca == -0.5
    assert item.tipo == TipoDivergencia.QUANTIDADE_MENOR
