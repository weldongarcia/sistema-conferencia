"""
Recálculo de divergências legadas.

Antes da BACKEND-01.1 as divergências eram gravadas pelo
GET /conferencia/{id}. Conferências abertas que não passaram
por um fluxo de escrita depois disso podem ter divergências
ausentes ou obsoletas na versão atual. Este script as
recalcula com a mesma regra dos fluxos de escrita
(recalcular_divergencias).

Regras:
- atua somente em conferências RASCUNHO e REABERTA;
- FINALIZADA, APROVADA, REPROVADA e demais status são
  ignorados e nunca alterados;
- recalcula somente a versão atual de cada conferência;
- dry-run é o padrão: nada é persistido;
- com --apply, tudo é gravado em uma única transação; em
  caso de erro, nenhuma alteração é mantida;
- idempotente: uma segunda execução não altera nada.

Uso (a partir de backend/):

    python -m scripts.recalcular_divergencias
    python -m scripts.recalcular_divergencias --apply
    python -m scripts.recalcular_divergencias --conferencia-id 12 --apply
"""

import argparse
import sys
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.enums.conferencia_enums import StatusConferencia
from app.models.conferencia import Conferencia
from app.services.divergencia_service import (
    ResumoRecalculo,
    recalcular_divergencias,
)


STATUS_PROCESSADOS = (
    StatusConferencia.RASCUNHO,
    StatusConferencia.REABERTA,
)


# ==========================================================
# RELATÓRIO
# ==========================================================

@dataclass
class Relatorio:
    aplicado: bool
    analisadas: list[ResumoRecalculo] = field(default_factory=list)
    ignoradas: list[tuple[int, str]] = field(default_factory=list)

    def _somar(self, campo):
        return sum(getattr(r, campo) for r in self.analisadas)

    @property
    def criar(self):
        return self._somar("criadas")

    @property
    def atualizar(self):
        return self._somar("atualizadas")

    @property
    def remover(self):
        return (
            self._somar("removidas")
            + self._somar("duplicadas_removidas")
        )

    @property
    def justificativas_preservadas(self):
        return self._somar("justificativas_preservadas")

    @property
    def justificativas_invalidadas(self):
        return self._somar("justificativas_invalidadas")

    @property
    def justificativas_removidas(self):
        return self._somar("justificativas_removidas")

    @property
    def total_alteracoes(self):
        return self.criar + self.atualizar + self.remover

    @property
    def conferencias_alteradas(self):
        return [r for r in self.analisadas if r.houve_alteracao]


# ==========================================================
# EXECUÇÃO
# ==========================================================

def executar(
    db: Session,
    aplicar: bool = False,
    conferencia_ids=None
) -> Relatorio:
    """
    Recalcula as divergências e devolve o relatório.

    aplicar=False: tudo é desfeito com rollback ao final.
    aplicar=True: um único commit ao final; qualquer erro
    desfaz todas as conferências e é propagado.
    """

    relatorio = Relatorio(aplicado=aplicar)

    consulta = db.query(Conferencia)

    if conferencia_ids:
        consulta = consulta.filter(
            Conferencia.id.in_(conferencia_ids)
        )

    try:

        for conferencia in consulta.order_by(Conferencia.id).all():

            if conferencia.status not in STATUS_PROCESSADOS:
                relatorio.ignoradas.append((
                    conferencia.id,
                    getattr(
                        conferencia.status,
                        "value",
                        str(conferencia.status)
                    ),
                ))
                continue

            relatorio.analisadas.append(
                recalcular_divergencias(db, conferencia)
            )

        if aplicar:
            db.commit()
        else:
            db.rollback()

    except Exception:
        db.rollback()
        raise

    return relatorio


# ==========================================================
# SAÍDA
# ==========================================================

def formatar(relatorio: Relatorio) -> str:
    modo = (
        "APLICADO"
        if relatorio.aplicado
        else "DRY-RUN (nada foi gravado)"
    )

    if relatorio.aplicado:
        acoes = ("criadas", "atualizadas", "removidas")
    else:
        acoes = ("a criar", "a atualizar", "a remover")

    linhas = [
        f"Recálculo de divergências legadas — {modo}",
        "",
    ]

    for r in relatorio.conferencias_alteradas:
        linhas.append(
            f"  conferência {r.conferencia_id} v{r.versao}: "
            f"criar={r.criadas} atualizar={r.atualizadas} "
            f"remover={r.removidas + r.duplicadas_removidas} "
            f"(duplicadas={r.duplicadas_removidas}) "
            f"justificativas invalidadas={r.justificativas_invalidadas} "
            f"removidas={r.justificativas_removidas}"
        )

    if relatorio.conferencias_alteradas:
        linhas.append("")

    status_ignorados = {}

    for _, status in relatorio.ignoradas:
        status_ignorados[status] = status_ignorados.get(status, 0) + 1

    ignoradas = ", ".join(
        f"{status}={total}"
        for status, total in sorted(status_ignorados.items())
    ) or "nenhuma"

    linhas += [
        f"Conferências analisadas (RASCUNHO/REABERTA): "
        f"{len(relatorio.analisadas)}",
        f"Conferências com alteração:                  "
        f"{len(relatorio.conferencias_alteradas)}",
        f"Conferências ignoradas por status:           "
        f"{len(relatorio.ignoradas)} ({ignoradas})",
        f"Divergências {acoes[0]}:".ljust(45) + f"{relatorio.criar}",
        f"Divergências {acoes[1]}:".ljust(45) + f"{relatorio.atualizar}",
        f"Divergências {acoes[2]}:".ljust(45) + f"{relatorio.remover}",
        "Justificativas preservadas:".ljust(45)
        + f"{relatorio.justificativas_preservadas}",
        (
            "Justificativas invalidadas:"
            if relatorio.aplicado
            else "Justificativas que seriam invalidadas:"
        ).ljust(45) + f"{relatorio.justificativas_invalidadas}",
        (
            "Justificativas removidas com a divergência:"
            if relatorio.aplicado
            else "Justificativas que seriam removidas:"
        ).ljust(45) + f"{relatorio.justificativas_removidas}",
        (
            "Total de alterações:"
            if relatorio.aplicado
            else "Total de alterações previstas:"
        ).ljust(45) + f"{relatorio.total_alteracoes}",
    ]

    if not relatorio.aplicado and relatorio.total_alteracoes:
        linhas += ["", "Para gravar, execute novamente com --apply."]

    return "\n".join(linhas)


# ==========================================================
# CLI
# ==========================================================

def main(argv=None, sessao_factory=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Recalcula divergências da versão atual de "
            "conferências RASCUNHO e REABERTA."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="grava as alterações (padrão: dry-run)",
    )

    parser.add_argument(
        "--conferencia-id",
        type=int,
        action="append",
        dest="conferencia_ids",
        help="limita a uma conferência (pode repetir)",
    )

    args = parser.parse_args(argv)

    if sessao_factory is None:
        from app.database.connection import SessionLocal
        sessao_factory = SessionLocal

    db = sessao_factory()

    try:
        relatorio = executar(
            db,
            aplicar=args.apply,
            conferencia_ids=args.conferencia_ids,
        )
    except Exception as erro:
        print(
            "ERRO: recálculo interrompido; nenhuma alteração "
            f"foi gravada. {type(erro).__name__}: {erro}",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    print(formatar(relatorio))

    return 0


if __name__ == "__main__":
    sys.exit(main())
