type EstiloStatus = {
  classes: string;
  indicador: string;
};

export const ESTILOS_STATUS: Record<string, EstiloStatus> = {
  RASCUNHO: {
    classes: "border-warning/30 bg-warning-soft text-warning-strong",
    indicador: "bg-warning",
  },

  REABERTA: {
    classes: "border-attention/30 bg-attention-soft text-attention-strong",
    indicador: "bg-attention",
  },

  FINALIZADA: {
    classes: "border-info/30 bg-info-soft text-info",
    indicador: "bg-info",
  },

  APROVADA: {
    classes: "border-success/30 bg-success-soft text-success-strong",
    indicador: "bg-success",
  },

  REPROVADA: {
    classes: "border-danger/30 bg-danger-soft text-danger",
    indicador: "bg-danger",
  },
};

const ESTILO_PADRAO: EstiloStatus = {
  classes: "border-line bg-canvas text-muted",
  indicador: "bg-muted",
};

export function estiloStatus(status: string): EstiloStatus {
  return ESTILOS_STATUS[status.toUpperCase()] ?? ESTILO_PADRAO;
}

export default function StatusBadge({ status }: { status: string }) {
  const { classes, indicador } = estiloStatus(status);

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${classes}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${indicador}`} />

      {status}
    </span>
  );
}
