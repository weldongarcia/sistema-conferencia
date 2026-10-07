from collections import defaultdict
from dataclasses import dataclass

from app.enums.conferencia_enums import TipoDivergencia
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
    # ======================================================

    resultado = []

    codigos = sorted(
        set(mapa_xml.keys())
        | set(mapa_contagem.keys())
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
        elif codigo not in mapa_contagem:
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