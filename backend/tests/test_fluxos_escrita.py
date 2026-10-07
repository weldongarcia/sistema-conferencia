"""
Fluxos de escrita que mantêm as divergências da versão atual:
sync, POST /contagens/, importação de XML, reabrir e fechar.

Os testes chamam os services diretamente, como as rotas fazem.
"""

import io
from types import SimpleNamespace

import pytest

from fastapi import HTTPException
from sqlalchemy import event

from app.enums.conferencia_enums import (
    StatusConferencia,
    TipoDivergencia,
    TipoJustificativa,
)
from app.models.conferencia import Conferencia
from app.models.conferencia_historico import ConferenciaHistorico
from app.models.contagem import Contagem
from app.models.divergencia import Divergencia
from app.models.item_nf import ItemNF
from app.schemas.contagem import ContagemCreate
from app.schemas.sincronizacao import SincronizacaoContagem
from app.services.conferencia_service import (
    comparar_conferencia,
    fechar_conferencia,
    reabrir_conferencia,
)
from app.services.contagem_services import criar_contagem
from app.services.divergencia_service import (
    calcular_comparacao,
    divergencia_corresponde,
)
from app.services.nfe_service import importar_xml
from app.services.sincronizacao_service import sincronizar_contagem

from conftest import fotografar


# ============================================================
# AUXILIARES
# ============================================================

@pytest.fixture
def conferente(fabrica):
    return fabrica.usuario(perfil="CONFERENTE", estabelecimento_id=1)


@pytest.fixture
def auditor(fabrica):
    return fabrica.usuario(perfil="AUDITOR", estabelecimento_id=None)


def snapshot(**quantidades):
    # snapshot(c10001=2) -> código "10001"
    return SincronizacaoContagem(itens=[
        {"codigo": codigo.lstrip("c"), "quantidade": quantidade}
        for codigo, quantidade in quantidades.items()
    ])


def linhas(db, conferencia, versao):
    db.expire_all()

    return {
        d.codigo: d
        for d in db.query(Divergencia).filter(
            Divergencia.conferencia_id == conferencia.id,
            Divergencia.versao == versao,
        )
    }


def resumo_linhas(db, conferencia, versao):
    return {
        codigo: (getattr(d.tipo, "value", d.tipo), d.xml, d.contado)
        for codigo, d in linhas(db, conferencia, versao).items()
    }


def xml_nfe(itens, chave="35260100000000000000550010000000011000000011"):
    dets = "".join(
        f"""
        <det nItem="{n}">
          <prod>
            <cProd>{codigo}</cProd>
            <xProd>Produto {codigo}</xProd>
            <qCom>{quantidade}</qCom>
          </prod>
        </det>"""
        for n, (codigo, quantidade) in enumerate(itens, start=1)
    )

    conteudo = f"""<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
      <NFe>
        <infNFe Id="NFe{chave}">
          <ide><nNF>123</nNF></ide>
          {dets}
        </infNFe>
      </NFe>
    </nfeProc>"""

    return SimpleNamespace(file=io.BytesIO(conteudo.encode("utf-8")))


def contar_commits(db):
    commits = []

    def registrar(sessao):
        commits.append(1)

    event.listen(db, "after_commit", registrar)

    return commits, lambda: event.remove(db, "after_commit", registrar)


# ============================================================
# REGRESSÃO DO SYNC
#
# Falhavam contra o sync anterior ao commit 4 (lógica inline).
# ============================================================

def conferencia_reaberta_com_v1(fabrica):
    """
    Versão 2 (REABERTA). Linhas da versão 1, todas justificadas:

    14001: mesmos valores que a v2 terá   -> sync antigo MOVIA
    14002: diferença zera na v2           -> sync antigo APAGAVA
    14003: valores diferentes na v2       -> sync antigo ALTERAVA
    """

    conferencia = fabrica.conferencia(
        status=StatusConferencia.REABERTA,
        versao=2,
        quantidade_reaberturas=1,
    )

    for codigo in ("14001", "14002", "14003"):
        fabrica.item_nf(conferencia, codigo, 5)

    for codigo, contado in (("14001", 2), ("14002", 3), ("14003", 4)):
        # Contagens da v1 já existem no servidor.
        fabrica.contagem(conferencia, codigo, contado)

        fabrica.divergencia(
            conferencia, codigo, xml=5, contado=contado,
            tipo=TipoDivergencia.QUANTIDADE_MENOR,
            versao=1,
            justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
            justificativa_descricao=f"Justificativa v1 {codigo}",
        )

    return conferencia


def sincronizar_v2(db, usuario, conferencia):
    sincronizar_contagem(
        db,
        conferencia.id,
        snapshot(c14001=2, c14002=5, c14003=1),
        usuario,
    )


def test_sync_nao_altera_divergencia_da_versao_anterior(
    db, fabrica, conferente
):
    conferencia = conferencia_reaberta_com_v1(fabrica)

    filtro_v1 = (
        Divergencia.conferencia_id == conferencia.id,
        Divergencia.versao == 1,
    )
    antes = fotografar(db, Divergencia, *filtro_v1)

    sincronizar_v2(db, conferente, conferencia)

    assert fotografar(db, Divergencia, *filtro_v1) == antes


def test_sync_nao_altera_valores_da_linha_v1_14003(
    db, fabrica, conferente
):
    conferencia = conferencia_reaberta_com_v1(fabrica)

    id_v1 = linhas(db, conferencia, 1)["14003"].id

    sincronizar_v2(db, conferente, conferencia)

    db.expire_all()
    linha = db.get(Divergencia, id_v1)

    assert (linha.versao, linha.contado) == (1, 4), (
        f"linha v1 id={id_v1} virou versao={linha.versao}, "
        f"contado={linha.contado}"
    )


def test_sync_nao_move_justificativa_da_v1_para_v2(
    db, fabrica, conferente
):
    conferencia = conferencia_reaberta_com_v1(fabrica)

    sincronizar_v2(db, conferente, conferencia)

    herdadas = {
        codigo: d.justificativa_descricao
        for codigo, d in linhas(db, conferencia, 2).items()
        if d.justificativa_descricao is not None
    }

    assert herdadas == {}, f"v2 herdou justificativas da v1: {herdadas}"

    # A v2 tem as próprias divergências, sem justificativa.
    assert resumo_linhas(db, conferencia, 2) == {
        "14001": ("QUANTIDADE_MENOR", 5, 2),
        "14003": ("QUANTIDADE_MENOR", 5, 1),
    }


def test_sync_nao_apaga_divergencia_da_versao_anterior(
    db, fabrica, conferente
):
    conferencia = conferencia_reaberta_com_v1(fabrica)

    sincronizar_v2(db, conferente, conferencia)

    assert set(linhas(db, conferencia, 1)) == {
        "14001",
        "14002",
        "14003",
    }


def test_sync_considera_contagem_criada_no_proprio_snapshot(
    db, fabrica, conferente
):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "18001", 5)

    sincronizar_contagem(
        db, conferencia.id, snapshot(c18001=5), conferente
    )

    gravadas = resumo_linhas(db, conferencia, 1)

    assert gravadas == {}, (
        f"snapshot enviou 18001=5 (igual à NF), sync gravou {gravadas}"
    )


def test_sync_usa_a_mesma_regra_de_calcular_comparacao(
    db, fabrica, conferente
):
    """
    17001: item da NF fora do snapshot (sem contagem)
    17002: NF 5, contado 2
    17003: duas linhas na NF (3 + 2), contado 5
    """

    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "17001", 5)
    fabrica.item_nf(conferencia, "17002", 5)
    fabrica.item_nf(conferencia, "17003", 3)
    fabrica.item_nf(conferencia, "17003", 2)

    sincronizar_contagem(
        db,
        conferencia.id,
        snapshot(c17002=2, c17003=5),
        conferente,
    )

    db.expire_all()

    calculado = {
        item.codigo: item
        for item in calcular_comparacao(
            db.query(ItemNF).filter_by(conferencia_id=conferencia.id).all(),
            db.query(Contagem).filter_by(conferencia_id=conferencia.id).all(),
        )
        if item.divergente
    }

    gravado = linhas(db, conferencia, 1)

    divergencias = []

    for codigo in sorted(set(calculado) | set(gravado)):
        item = calculado.get(codigo)
        linha = gravado.get(codigo)

        if item is None or linha is None or not divergencia_corresponde(
            linha, item
        ):
            divergencias.append((
                codigo,
                "calculo:",
                item and (item.tipo.value, item.xml, item.contado),
                "sync:",
                linha and (
                    getattr(linha.tipo, "value", linha.tipo),
                    linha.xml,
                    linha.contado,
                ),
            ))

    assert divergencias == []

    assert resumo_linhas(db, conferencia, 1) == {
        "17001": ("PRODUTO_NAO_ENCONTRADO", 5, 0),
        "17002": ("QUANTIDADE_MENOR", 5, 2),
    }


def test_sync_zera_produto_a_mais_ausente_do_snapshot(
    db, fabrica, conferente
):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "17101", 1)

    sincronizar_contagem(
        db, conferencia.id, snapshot(c17101=1, c17102=2), conferente
    )
    assert set(linhas(db, conferencia, 1)) == {"17102"}

    # 17102 sai do snapshot: contagem vai a 0 e deixa de divergir.
    sincronizar_contagem(
        db, conferencia.id, snapshot(c17101=1), conferente
    )
    assert linhas(db, conferencia, 1) == {}


# ============================================================
# POST /contagens/
# ============================================================

def test_post_contagem_recalcula_divergencias(db, fabrica, conferente):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "20001", 5)

    criar_contagem(
        db,
        ContagemCreate(
            conferencia_id=conferencia.id, codigo="20001", quantidade=2
        ),
        conferente,
    )

    assert resumo_linhas(db, conferencia, 1) == {
        "20001": ("QUANTIDADE_MENOR", 5, 2),
    }

    # A segunda leitura soma à existente e zera a divergência.
    criar_contagem(
        db,
        ContagemCreate(
            conferencia_id=conferencia.id, codigo="20001", quantidade=3
        ),
        conferente,
    )

    assert resumo_linhas(db, conferencia, 1) == {}


def test_post_contagem_produto_fora_da_nf(db, fabrica, conferente):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "20002", 1)

    criar_contagem(
        db,
        ContagemCreate(
            conferencia_id=conferencia.id,
            codigo="20003",
            quantidade=4,
            incluir_na_conferencia=True,
        ),
        conferente,
    )

    assert resumo_linhas(db, conferencia, 1) == {
        "20002": ("PRODUTO_NAO_ENCONTRADO", 1, 0),
        "20003": ("PRODUTO_A_MAIS", 0, 4),
    }


# ============================================================
# IMPORTAÇÃO DE XML
# ============================================================

def test_importar_xml_recalcula_e_mantem_contrato(db, fabrica):
    conferencia = fabrica.conferencia()

    # Contagem feita antes do XML.
    fabrica.contagem(conferencia, "21001", 2)

    resposta = importar_xml(
        db,
        xml_nfe([("21001", "5.0000"), ("21002", "1"), ("21002", "2")]),
        conferencia.id,
    )

    assert set(resposta) == {
        "msg",
        "nota_id",
        "conferencia_id",
        "numero_nf",
        "chave_acesso",
        "total_itens",
    }
    assert resposta["msg"] == "Nota importada com sucesso"
    assert resposta["numero_nf"] == "123"
    assert resposta["total_itens"] == 2

    assert resumo_linhas(db, conferencia, 1) == {
        "21001": ("QUANTIDADE_MENOR", 5, 2),
        "21002": ("PRODUTO_NAO_ENCONTRADO", 3, 0),
    }


# ============================================================
# REABRIR
# ============================================================

def test_reabrir_cria_divergencias_da_nova_versao(
    db, fabrica, auditor, monkeypatch
):
    conferencia = fabrica.conferencia(status=StatusConferencia.FINALIZADA)

    fabrica.item_nf(conferencia, "22001", 5)
    fabrica.item_nf(conferencia, "22002", 5)
    fabrica.contagem(conferencia, "22001", 3)
    fabrica.contagem(conferencia, "22002", 5)

    fabrica.divergencia(
        conferencia, "22001", xml=5, contado=3,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
        justificativa_tipo=TipoJustificativa.ERRO_FORNECEDOR,
        justificativa_descricao="Justificativa v1",
    )

    filtro_v1 = (
        Divergencia.conferencia_id == conferencia.id,
        Divergencia.versao == 1,
    )
    v1_antes = fotografar(db, Divergencia, *filtro_v1)

    # registrar_historico faz o commit da reabertura. No momento em
    # que é chamado, nenhum commit pode ter ocorrido e as divergências
    # da v2 já precisam estar na mesma transação.
    import app.services.conferencia_service as servico

    commits, remover = contar_commits(db)
    registrar_original = servico.registrar_historico
    no_historico = {}

    def registrar_espiao(**kwargs):
        no_historico["commits"] = len(commits)
        no_historico["divergencias_v2"] = db.query(Divergencia).filter(
            Divergencia.conferencia_id == conferencia.id,
            Divergencia.versao == 2,
        ).count()
        return registrar_original(**kwargs)

    monkeypatch.setattr(servico, "registrar_historico", registrar_espiao)

    try:
        resposta = reabrir_conferencia(
            db=db,
            conferencia_id=conferencia.id,
            usuario_id=auditor.id,
            motivo="Recontar",
        )
    finally:
        remover()

    assert no_historico == {"commits": 0, "divergencias_v2": 1}

    assert resposta["versao"] == 2
    assert resposta["status"] == "REABERTA"
    assert resposta["quantidade_reaberturas"] == 1

    assert fotografar(db, Divergencia, *filtro_v1) == v1_antes

    v2 = linhas(db, conferencia, 2)

    assert set(v2) == {"22001"}
    assert v2["22001"].justificativa_tipo is None
    assert v2["22001"].justificativa_descricao is None

    historico = db.query(ConferenciaHistorico).filter_by(
        conferencia_id=conferencia.id, acao="REABERTA"
    ).one()

    assert (historico.versao, historico.motivo) == (2, "Recontar")


# ============================================================
# FECHAR
# ============================================================

def test_fechar_sem_get_anterior_bloqueia_e_grava_pendencias(
    db, fabrica, conferente
):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "23001", 5)
    fabrica.contagem(conferencia, "23001", 2)

    # Nenhuma divergência gravada: ninguém chamou o GET.
    assert linhas(db, conferencia, 1) == {}

    with pytest.raises(HTTPException) as erro:
        fechar_conferencia(
            db=db,
            conferencia_id=conferencia.id,
            usuario_id=conferente.id,
        )

    assert erro.value.status_code == 400

    # O fechamento foi bloqueado, mas a pendência ficou gravada
    # (com id) para poder ser justificada.
    db.rollback()

    assert resumo_linhas(db, conferencia, 1) == {
        "23001": ("QUANTIDADE_MENOR", 5, 2),
    }
    assert db.get(Conferencia, conferencia.id).status == (
        StatusConferencia.RASCUNHO
    )


def test_fechar_finaliza_quando_divergencias_justificadas(
    db, fabrica, conferente
):
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "23002", 5)
    fabrica.contagem(conferencia, "23002", 2)

    with pytest.raises(HTTPException):
        fechar_conferencia(
            db=db, conferencia_id=conferencia.id, usuario_id=conferente.id
        )

    db.rollback()

    divergencia = linhas(db, conferencia, 1)["23002"]
    divergencia.justificativa_tipo = TipoJustificativa.ERRO_FORNECEDOR
    divergencia.justificativa_descricao = "Faltou na entrega"
    db.commit()

    resposta = fechar_conferencia(
        db=db, conferencia_id=conferencia.id, usuario_id=conferente.id
    )

    assert resposta == {"msg": "Conferência finalizada com sucesso"}

    db.expire_all()
    assert db.get(Conferencia, conferencia.id).status == (
        StatusConferencia.FINALIZADA
    )

    # A justificativa sobreviveu ao recálculo do fechamento.
    assert linhas(db, conferencia, 1)["23002"].justificativa_descricao == (
        "Faltou na entrega"
    )


def test_fechar_remove_pendencia_obsoleta_e_finaliza(
    db, fabrica, conferente
):
    # Divergência sem justificativa gravada por um GET antigo;
    # a contagem foi corrigida depois sem novo GET.
    conferencia = fabrica.conferencia()

    fabrica.item_nf(conferencia, "23003", 5)
    fabrica.contagem(conferencia, "23003", 5)

    fabrica.divergencia(
        conferencia, "23003", xml=5, contado=2,
        tipo=TipoDivergencia.QUANTIDADE_MENOR,
    )

    resposta = fechar_conferencia(
        db=db, conferencia_id=conferencia.id, usuario_id=conferente.id
    )

    assert resposta == {"msg": "Conferência finalizada com sucesso"}
    assert linhas(db, conferencia, 1) == {}


# ============================================================
# VERSÕES ANTERIORES NUNCA SÃO ALTERADAS
# ============================================================

def fluxo_sync(db, conferencia, conferente, auditor):
    sincronizar_contagem(
        db, conferencia.id, snapshot(c14001=2, c14002=5), conferente
    )


def fluxo_contagem(db, conferencia, conferente, auditor):
    criar_contagem(
        db,
        ContagemCreate(
            conferencia_id=conferencia.id, codigo="14002", quantidade=2
        ),
        conferente,
    )


def fluxo_importar_xml(db, conferencia, conferente, auditor):
    importar_xml(db, xml_nfe([("14004", "1")]), conferencia.id)


def fluxo_fechar(db, conferencia, conferente, auditor):
    with pytest.raises(HTTPException):
        fechar_conferencia(
            db=db, conferencia_id=conferencia.id, usuario_id=conferente.id
        )

    db.rollback()


def fluxo_reabrir(db, conferencia, conferente, auditor):
    conferencia.status = StatusConferencia.FINALIZADA
    db.commit()

    reabrir_conferencia(
        db=db,
        conferencia_id=conferencia.id,
        usuario_id=auditor.id,
        motivo="Nova recontagem",
    )


def fluxo_get(db, conferencia, conferente, auditor):
    comparar_conferencia(db, conferencia.id, auditor)


@pytest.mark.parametrize(
    "fluxo",
    [
        fluxo_sync,
        fluxo_contagem,
        fluxo_importar_xml,
        fluxo_fechar,
        fluxo_reabrir,
        fluxo_get,
    ],
    ids=["sync", "contagem", "importar_xml", "fechar", "reabrir", "get"],
)
def test_fluxo_nao_altera_versoes_anteriores(
    db, fabrica, conferente, auditor, fluxo
):
    conferencia = conferencia_reaberta_com_v1(fabrica)

    anteriores = (
        Divergencia.conferencia_id == conferencia.id,
        Divergencia.versao < conferencia.versao,
    )

    antes = fotografar(db, Divergencia, *anteriores)
    assert len(antes) == 3

    fluxo(db, conferencia, conferente, auditor)

    assert fotografar(db, Divergencia, *anteriores) == antes

    # Nenhuma justificativa da v1 aparece em versões novas.
    db.expire_all()

    novas = db.query(Divergencia).filter(
        Divergencia.conferencia_id == conferencia.id,
        Divergencia.versao >= 2,
    ).all()

    assert all(d.justificativa_descricao is None for d in novas)
