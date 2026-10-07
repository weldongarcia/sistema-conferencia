"""
Migração de senhas legadas (texto puro) para Argon2id — SEC-01A.

Complementa a migração no primeiro login (estratégia D): converte as
senhas de usuários que ainda não entraram desde a implantação.

Regras:
- dry-run é o padrão: nada é gravado;
- --apply grava tudo em uma única transação; qualquer erro desfaz tudo;
- idempotente: senhas já em Argon2id não são alteradas;
- formatos desconhecidos ($... que não seja Argon2id, ou vazio) não
  são alterados e são apenas contados;
- senhas legadas acima do limite de tamanho não são migradas (o usuário
  não conseguiria entrar com elas) e são apenas contadas;
- nunca imprime senhas, hashes ou usernames; somente ids e contagens.

Uso (a partir de backend/):

    python -m scripts.migrar_senhas
    python -m scripts.migrar_senhas --apply
"""

import argparse
import sys
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.security import (
    SENHA_ARGON2ID,
    SENHA_LEGADA,
    classificar_senha_armazenada,
    gerar_hash,
    senha_dentro_do_limite,
)
from app.models.usuario import Usuario


@dataclass
class RelatorioSenhas:
    aplicado: bool
    total: int = 0
    ja_argon2id: int = 0
    legadas_migradas: list[int] = field(default_factory=list)
    legadas_fora_do_limite: list[int] = field(default_factory=list)
    formato_desconhecido: list[int] = field(default_factory=list)


def executar(db: Session, aplicar: bool = False) -> RelatorioSenhas:
    relatorio = RelatorioSenhas(aplicado=aplicar)

    try:

        for usuario in db.query(Usuario).order_by(Usuario.id).all():

            relatorio.total += 1

            formato = classificar_senha_armazenada(usuario.senha)

            if formato == SENHA_ARGON2ID:
                relatorio.ja_argon2id += 1
                continue

            if formato != SENHA_LEGADA:
                relatorio.formato_desconhecido.append(usuario.id)
                continue

            if not senha_dentro_do_limite(usuario.senha):
                relatorio.legadas_fora_do_limite.append(usuario.id)
                continue

            usuario.senha = gerar_hash(usuario.senha)
            relatorio.legadas_migradas.append(usuario.id)

        if aplicar:
            db.commit()
        else:
            db.rollback()

    except Exception:
        db.rollback()
        raise

    return relatorio


def _ids(ids):
    return ", ".join(str(i) for i in ids) if ids else "-"


def formatar(relatorio: RelatorioSenhas) -> str:
    modo = (
        "APLICADO"
        if relatorio.aplicado
        else "DRY-RUN (nada foi gravado)"
    )

    migradas = (
        "Senhas legadas migradas:"
        if relatorio.aplicado
        else "Senhas legadas a migrar:"
    )

    linhas = [
        f"Migração de senhas para Argon2id — {modo}",
        "",
        "Usuários analisados:".ljust(40) + f"{relatorio.total}",
        "Já em Argon2id (inalterados):".ljust(40)
        + f"{relatorio.ja_argon2id}",
        migradas.ljust(40) + f"{len(relatorio.legadas_migradas)}",
        "Legadas acima do limite (ignoradas):".ljust(40)
        + f"{len(relatorio.legadas_fora_do_limite)}",
        "Formato desconhecido (ignorados):".ljust(40)
        + f"{len(relatorio.formato_desconhecido)}",
        "",
        f"Ids migrados: {_ids(relatorio.legadas_migradas)}",
        f"Ids acima do limite: {_ids(relatorio.legadas_fora_do_limite)}",
        f"Ids com formato desconhecido: "
        f"{_ids(relatorio.formato_desconhecido)}",
    ]

    if not relatorio.aplicado and relatorio.legadas_migradas:
        linhas += ["", "Para gravar, execute novamente com --apply."]

    return "\n".join(linhas)


def main(argv=None, sessao_factory=None) -> int:
    parser = argparse.ArgumentParser(
        description="Converte senhas legadas em texto puro para Argon2id."
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="grava as alterações (padrão: dry-run)",
    )

    args = parser.parse_args(argv)

    if sessao_factory is None:
        from app.database.connection import SessionLocal
        sessao_factory = SessionLocal

    db = sessao_factory()

    try:
        relatorio = executar(db, aplicar=args.apply)
    except Exception as erro:
        # Somente o tipo do erro: a mensagem poderia conter dados.
        print(
            "ERRO: migração interrompida; nenhuma alteração foi gravada. "
            f"{type(erro).__name__}",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    print(formatar(relatorio))

    return 0


if __name__ == "__main__":
    sys.exit(main())
