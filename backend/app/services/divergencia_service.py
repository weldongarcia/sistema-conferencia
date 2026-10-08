from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.conferencia import Conferencia
from app.models.contagem import Contagem
from app.models.divergencia import Divergencia
from app.models.item_nf import ItemNF

from app.enums.conferencia_enums import (
    StatusConferencia,
    TipoDivergencia
)

from app.utils.codigo import normalizar_codigo


# ==========================================================
# ITEM COMPARADO
# ==========================================================

@dataclass(frozen=True)
class ItemComparado:
    """
    Resultado da comparação NF x contagem para um código.

    tipo e origem são None quando não há divergência.
    """

    codigo: str
    descricao: str | None
    xml: float
    contado: float
    diferenca: float
    tipo: TipoDivergencia | None
    origem: str | None

    @property
    def divergente(self) -> bool:
        return self.tipo is not None


# ==========================================================
# CALCULAR COMPARAÇÃO
#
# Fonte única da regra de divergência.
# Não acessa o banco: recebe itens da NF e contagens já
# carregados e devolve um ItemComparado por código.
# ==========================================================

def calcular_comparacao(
    itens_nf,
    contagens
) -> list[ItemComparado]:

    # ======================================================
    # MAPA XML
    #
    # Linhas repetidas do mesmo código são consolidadas.
    # ======================================================

    mapa_xml = defaultdict(float)
    mapa_descricao = {}

    for item in itens_nf:

        codigo = normalizar_codigo(
            item.codigo
        )

        mapa_xml[codigo] += float(
            item.quantidade
        )

        if codigo not in mapa_descricao:
            mapa_descricao[codigo] = item.descricao

    # ======================================================
    # MAPA CONTAGEM
    # ======================================================

    mapa_contagem = defaultdict(float)

    for contagem in contagens:

        codigo = normalizar_codigo(
            contagem.codigo
        )

        mapa_contagem[codigo] += float(
            contagem.quantidade
        )

    # ======================================================
    # COMPARAÇÃO
    #
    # Contagem 0 equivale a ausência de contagem, conforme
    # a regra do snapshot:
    #
    # - item da NF com contagem 0 = PRODUTO_NAO_ENCONTRADO;
    # - produto fora da NF com contagem 0 não é divergência
    #   e não aparece no resultado.
    # ======================================================

    resultado = []

    codigos = sorted(
        set(mapa_xml.keys())
        | {
            codigo
            for codigo, quantidade in mapa_contagem.items()
            if quantidade != 0
        }
    )

    for codigo in codigos:

        xml_qtd = mapa_xml.get(codigo, 0)
        cont_qtd = mapa_contagem.get(codigo, 0)

        diferenca = cont_qtd - xml_qtd

        tipo = None
        origem = None

        # Produto não existe na NF
        if codigo not in mapa_xml:
            tipo = TipoDivergencia.PRODUTO_A_MAIS
            origem = "FORA_NOTA"

        # Produto da NF não foi contado
        elif cont_qtd == 0:
            tipo = TipoDivergencia.PRODUTO_NAO_ENCONTRADO
            origem = "NOTA"

        elif diferenca < 0:
            tipo = TipoDivergencia.QUANTIDADE_MENOR
            origem = "NOTA"

        elif diferenca > 0:
            tipo = TipoDivergencia.QUANTIDADE_MAIOR
            origem = "NOTA"

        resultado.append(ItemComparado(
            codigo=codigo,
            descricao=mapa_descricao.get(codigo),
            xml=xml_qtd,
            contado=cont_qtd,
            diferenca=diferenca,
            tipo=tipo,
            origem=origem,
        ))

    return resultado


# ==========================================================
# QUANTIDADE PERSISTIDA
#
# As colunas de Divergencia são Integer. A conversão é feita
# aqui, de forma explícita, para que gravação e comparação
# usem exatamente o mesmo valor.
#
# round() arredonda meio para par, como o PostgreSQL faz ao
# gravar float em coluna integer. Quantidade fracionada
# continua sendo dívida técnica de domínio.
# ==========================================================

def quantidade_persistida(valor) -> int:
    return int(round(valor))


def valores_persistidos(item: ItemComparado) -> dict:
    xml = quantidade_persistida(item.xml)
    contado = quantidade_persistida(item.contado)

    return {
        "xml": xml,
        "contado": contado,
        "diferenca": contado - xml,
        "tipo": item.tipo,
        "origem": item.origem,
    }


def _tipo(valor):
    if valor is None:
        return None

    return TipoDivergencia(
        valor.value if hasattr(valor, "value") else valor
    )


# ==========================================================
# DIVERGÊNCIA CORRESPONDE AO CÁLCULO
#
# True quando a divergência gravada representa a mesma
# situação do item calculado. Quando não corresponde, a
# justificativa gravada não vale para a situação atual.
# ==========================================================

def divergencia_corresponde(
    divergencia: Divergencia,
    item: ItemComparado
) -> bool:

    if not item.divergente:
        return False

    esperado = valores_persistidos(item)

    return (
        divergencia.xml == esperado["xml"]
        and divergencia.contado == esperado["contado"]
        and divergencia.diferenca == esperado["diferenca"]
        and _tipo(divergencia.tipo) == esperado["tipo"]
        and divergencia.origem == esperado["origem"]
    )


# ==========================================================
# RECALCULAR DIVERGÊNCIAS
# ==========================================================

STATUS_RECALCULAVEIS = {
    StatusConferencia.RASCUNHO,
    StatusConferencia.EM_CONFERENCIA,
    StatusConferencia.REABERTA,
}


@dataclass
class ResumoRecalculo:
    conferencia_id: int
    versao: int
    ignorado: bool = False
    criadas: int = 0
    atualizadas: int = 0
    removidas: int = 0
    duplicadas_removidas: int = 0
    justificativas_invalidadas: int = 0

    # Auditoria: não são alterações por si só.
    justificativas_preservadas: int = 0
    justificativas_removidas: int = 0

    @property
    def houve_alteracao(self) -> bool:
        return any((
            self.criadas,
            self.atualizadas,
            self.removidas,
            self.duplicadas_removidas,
        ))


def _justificada(divergencia) -> bool:
    return (
        divergencia.justificativa_tipo is not None
        or divergencia.justificativa_descricao is not None
    )


def escolher_divergencia(divergencias):
    """
    Entre linhas duplicadas do mesmo código na mesma versão,
    mantém a justificada mais antiga; sem justificada, a mais
    antiga.
    """

    return min(
        divergencias,
        key=lambda d: (d.justificativa_tipo is None, d.id)
    )


def recalcular_divergencias(
    db: Session,
    conferencia: Conferencia,
    estados_permitidos=STATUS_RECALCULAVEIS
) -> ResumoRecalculo:
    """
    Sincroniza as divergências gravadas da versão atual com o
    cálculo de calcular_comparacao.

    - Atua somente na versão atual da conferência.
    - Não grava em status fora de estados_permitidos (padrão:
      STATUS_RECALCULAVEIS; versões finalizadas ou auditadas
      ficam intactas). A aprovação passa explicitamente
      FINALIZADA para validar a versão antes de aprová-la.
    - Invalida a justificativa somente quando a divergência
      muda materialmente.
    - Não faz commit; executa flush antes de ler (para ver
      contagens e itens pendentes do fluxo chamador) e depois
      de gravar (para que consultas seguintes na mesma sessão
      vejam o resultado).
    """

    versao = conferencia.versao

    resumo = ResumoRecalculo(
        conferencia_id=conferencia.id,
        versao=versao,
    )

    if conferencia.status not in estados_permitidos:
        resumo.ignorado = True
        return resumo

    db.flush()

    # ======================================================
    # DADOS
    # ======================================================

    itens_nf = (
        db.query(ItemNF)
        .filter(ItemNF.conferencia_id == conferencia.id)
        .all()
    )

    contagens = (
        db.query(Contagem)
        .filter(Contagem.conferencia_id == conferencia.id)
        .all()
    )

    divergencias = (
        db.query(Divergencia)
        .filter(
            Divergencia.conferencia_id == conferencia.id,
            Divergencia.versao == versao
        )
        .order_by(Divergencia.id)
        .all()
    )

    comparacao = {
        item.codigo: item
        for item in calcular_comparacao(itens_nf, contagens)
    }

    # ======================================================
    # AGRUPAR DIVERGÊNCIAS GRAVADAS POR CÓDIGO
    # ======================================================

    gravadas_por_codigo = defaultdict(list)

    for divergencia in divergencias:
        gravadas_por_codigo[
            normalizar_codigo(divergencia.codigo)
        ].append(divergencia)

    mapa_divergencias = {}

    for codigo, gravadas in gravadas_por_codigo.items():

        mantida = escolher_divergencia(gravadas)

        mapa_divergencias[codigo] = mantida

        for duplicada in gravadas:
            if duplicada is not mantida:
                db.delete(duplicada)
                resumo.duplicadas_removidas += 1

                if _justificada(duplicada):
                    resumo.justificativas_removidas += 1

    # ======================================================
    # REMOVER DIVERGÊNCIAS QUE DEIXARAM DE EXISTIR
    # ======================================================

    for codigo, divergencia in mapa_divergencias.items():

        item = comparacao.get(codigo)

        if item is None or not item.divergente:
            db.delete(divergencia)
            resumo.removidas += 1

            if _justificada(divergencia):
                resumo.justificativas_removidas += 1

    # ======================================================
    # CRIAR / ATUALIZAR
    # ======================================================

    for codigo, item in comparacao.items():

        if not item.divergente:
            continue

        valores = valores_persistidos(item)

        divergencia = mapa_divergencias.get(codigo)

        if divergencia is None:

            db.add(Divergencia(
                conferencia_id=conferencia.id,
                codigo=codigo,
                versao=versao,
                **valores
            ))

            resumo.criadas += 1

            continue

        if divergencia_corresponde(divergencia, item):

            if _justificada(divergencia):
                resumo.justificativas_preservadas += 1

            continue

        for campo, valor in valores.items():
            setattr(divergencia, campo, valor)

        if _justificada(divergencia):
            resumo.justificativas_invalidadas += 1

        divergencia.justificativa_tipo = None
        divergencia.justificativa_descricao = None

        resumo.atualizadas += 1

    db.flush()

    return resumo


# ==========================================================
# LEGADO
#
# Sem uso conhecido. Mantida até confirmação de remoção.
# ==========================================================

def criar_divergencia_fora_nota(item_id, usuario_id):

    return Divergencia(
        conferencia_item_id=item_id,
        tipo="PRODUTO_A_MAIS",
        justificativa_tipo="OUTROS",
        origem="FORA_NOTA",
        usuario_id=usuario_id
    )