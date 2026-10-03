import type { ReactNode } from "react";

type EmptyStateProps = {
  icone: ReactNode;
  titulo: string;
  descricao: string;
  acao?: ReactNode;
};

export default function EmptyState({
  icone,
  titulo,
  descricao,
  acao,
}: EmptyStateProps) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-line bg-canvas text-muted">
        {icone}
      </div>

      <p className="font-medium text-ink">{titulo}</p>

      <p className="mt-2 text-sm text-muted">{descricao}</p>

      {acao}
    </div>
  );
}
