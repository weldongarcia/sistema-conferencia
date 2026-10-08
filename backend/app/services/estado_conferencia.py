"""
Máquina de estados da conferência (BACKEND-02A).

Fonte única de quais operações são permitidas em cada estado. Toda
operação que altera uma conferência deve chamar
exigir_operacao_permitida antes de gravar.

Fluxo:

    RASCUNHO --fechar--> FINALIZADA --aprovar--> APROVADA (final)
                         FINALIZADA --reprovar--> REPROVADA
                         FINALIZADA --reabrir--> REABERTA (nova versão)
                         REPROVADA  --reabrir--> REABERTA (nova versão)
    REABERTA --fechar--> FINALIZADA

Somente RASCUNHO e REABERTA são editáveis. EM_CONFERENCIA e
EM_AUDITORIA existem no enum mas não são atribuídos por nenhum fluxo e
não permitem nenhuma operação.
"""

from enum import Enum

from fastapi import HTTPException

from app.enums.conferencia_enums import StatusConferencia


class Operacao(str, Enum):
    CONTAGEM = "CONTAGEM"
    SINCRONIZACAO = "SINCRONIZACAO"
    JUSTIFICAR = "JUSTIFICAR"
    FECHAR = "FECHAR"
    APROVAR = "APROVAR"
    REPROVAR = "REPROVAR"
    REABRIR = "REABRIR"
    IMPORTAR_XML = "IMPORTAR_XML"


ESTADOS_EDITAVEIS = frozenset({
    StatusConferencia.RASCUNHO,
    StatusConferencia.REABERTA,
})


# ==========================================================
# OPERAÇÃO -> ESTADOS PERMITIDOS
# ==========================================================

ESTADOS_PERMITIDOS = {
    Operacao.CONTAGEM: ESTADOS_EDITAVEIS,
    Operacao.SINCRONIZACAO: ESTADOS_EDITAVEIS,
    Operacao.JUSTIFICAR: ESTADOS_EDITAVEIS,
    Operacao.FECHAR: ESTADOS_EDITAVEIS,
    Operacao.IMPORTAR_XML: ESTADOS_EDITAVEIS,
    Operacao.APROVAR: frozenset({
        StatusConferencia.FINALIZADA,
    }),
    Operacao.REPROVAR: frozenset({
        StatusConferencia.FINALIZADA,
    }),
    Operacao.REABRIR: frozenset({
        StatusConferencia.FINALIZADA,
        StatusConferencia.REPROVADA,
    }),
}


# Mensagens das respostas 400. {status} recebe o valor do estado atual.
MENSAGENS = {
    Operacao.CONTAGEM: (
        "Não é possível registrar contagem em uma conferência "
        "com status {status}."
    ),
    Operacao.SINCRONIZACAO: (
        "Não é possível sincronizar contagens de uma conferência "
        "com status {status}."
    ),
    Operacao.JUSTIFICAR: (
        "Não é possível justificar divergência de uma conferência "
        "com status {status}."
    ),
    Operacao.FECHAR: (
        "Não é possível fechar uma conferência com status {status}."
    ),
    Operacao.IMPORTAR_XML: (
        "Não é possível importar XML para uma conferência "
        "com status {status}."
    ),
    Operacao.APROVAR: (
        "Somente conferências finalizadas podem ser aprovadas."
    ),
    Operacao.REPROVAR: (
        "Somente conferências finalizadas podem ser reprovadas."
    ),
    Operacao.REABRIR: (
        "Somente conferências finalizadas ou reprovadas "
        "podem ser reabertas."
    ),
}


def _valor(status) -> str:
    return getattr(status, "value", str(status))


def operacao_permitida(status, operacao: Operacao) -> bool:
    return status in ESTADOS_PERMITIDOS[operacao]


def exigir_operacao_permitida(conferencia, operacao: Operacao) -> None:
    """
    Recusa com 400 a operação que o estado atual não permite.
    Deve ser chamada antes de qualquer alteração no banco.
    """

    if operacao_permitida(conferencia.status, operacao):
        return

    raise HTTPException(
        status_code=400,
        detail=MENSAGENS[operacao].format(
            status=_valor(conferencia.status)
        ),
    )
