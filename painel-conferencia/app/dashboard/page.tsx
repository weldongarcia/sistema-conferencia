"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "../../components/layout/AppShell";

import {
  buscarConferencias,
  buscarUsuarioAtual,
  criarConferencia,
} from "../../services/api";

type Usuario = {
  id: number;
  username: string;
  perfil: string;
  estabelecimento_id: number | null;
};

type Conferencia = {
  id: number;
  estabelecimento_id: number;
  usuario_id: number;
  status: string;
  data_inicio: string;
};

export default function DashboardPage() {
  const router = useRouter();

  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [conferencias, setConferencias] = useState<Conferencia[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    async function carregar() {
      try {
        const token = localStorage.getItem("token");

        if (!token) {
          router.push("/login");
          return;
        }

        const [dadosUsuario, dadosConferencias] = await Promise.all([
          buscarUsuarioAtual(token),
          buscarConferencias(token),
        ]);

        setUsuario(dadosUsuario);
        setConferencias(dadosConferencias);
      } catch (error) {
        console.error(error);

        setErro(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar o Dashboard.",
        );
      } finally {
        setCarregando(false);
      }
    }

    carregar();
  }, [router]);

  function formatarData(data: string) {
    return new Date(data).toLocaleString("pt-BR");
  }

  function contarStatus(status: string) {
    return conferencias.filter(
      (conferencia) => conferencia.status.toUpperCase() === status,
    ).length;
  }

  async function novaConferencia() {
    if (carregando) return;

    try {
      setCarregando(true);
      setErro("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      const conferencia = await criarConferencia(token);

      router.push(`/dashboard/conferencia/${conferencia.id}`);
    } catch (error) {
      console.error(error);

      setErro(
        error instanceof Error
          ? error.message
          : "Não foi possível criar a conferência.",
      );

      setCarregando(false);
    }
  }

  function sair() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    localStorage.removeItem("perfil");

    router.push("/login");
  }

  function nomeEstabelecimento() {
    if (!usuario?.estabelecimento_id) {
      return "Não vinculado";
    }

    return `Código ${usuario.estabelecimento_id}`;
  }

  const total = conferencias.length;
  const rascunho = contarStatus("RASCUNHO");
  const reaberta = contarStatus("REABERTA");
  const aprovada = contarStatus("APROVADA");
  const finalizada = contarStatus("FINALIZADA");

  const menuItems = [
    {
      label: "Dashboard",
      href: "/dashboard",
      icon: <DashboardIcon />,
    },
    {
      label: "Conferências",
      href: "/dashboard",
      icon: <ClipboardIcon />,
    },
  ];

  if (carregando) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas text-ink">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-line border-t-brand-light" />

          <p className="text-sm text-muted">Carregando painel...</p>
        </div>
      </main>
    );
  }

  return (
    <AppShell
      usuario={usuario?.username}
      perfil={usuario?.perfil}
      menuItems={menuItems}
      onLogout={sair}
    >
      <div className="mx-auto w-full max-w-[1500px] p-5 sm:p-8">
        {/* =====================================================
            CABEÇALHO
        ====================================================== */}

        <section className="mb-8">
          <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-brand-light" />

                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-light">
                  {usuario?.perfil || "Usuário"}
                </p>
              </div>

              <h1 className="text-3xl font-bold tracking-tight text-brand sm:text-4xl">
                Dashboard
              </h1>

              <p className="mt-2 text-sm text-muted">
                Acompanhe as conferências do seu estabelecimento.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="rounded-xl border border-line bg-white px-4 py-3 shadow-card">
                <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted">
                  Estabelecimento
                </p>

                <p className="mt-1 text-sm font-semibold text-ink">
                  {nomeEstabelecimento()}
                </p>
              </div>

              <button
                onClick={novaConferencia}
                disabled={carregando}
                className="inline-flex h-[46px] items-center justify-center gap-2 rounded-xl bg-brand px-5 text-sm font-semibold text-white shadow-button transition hover:bg-brand-light disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="text-lg leading-none">+</span>

                {carregando ? "Criando..." : "Nova Conferência"}
              </button>
            </div>
          </div>
        </section>

        {/* =====================================================
            ERRO
        ====================================================== */}

        {erro && (
          <div className="mb-6 rounded-xl border border-danger/30 bg-danger-soft p-5">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-danger">
                <AlertIcon />
              </div>

              <div>
                <p className="font-semibold text-danger">
                  Erro ao carregar o Dashboard
                </p>

                <p className="mt-1 text-sm text-danger">{erro}</p>
              </div>
            </div>
          </div>
        )}

        {/* =====================================================
            INDICADORES
        ====================================================== */}

        {!erro && (
          <>
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <StatCard
                titulo="Total"
                valor={total}
                descricao="Conferências registradas"
                destaque="default"
              />

              <StatCard
                titulo="Rascunhos"
                valor={rascunho}
                descricao="Em preparação"
                destaque="warning"
              />

              <StatCard
                titulo="Reabertas"
                valor={reaberta}
                descricao="Exigem atenção"
                destaque="orange"
              />

              <StatCard
                titulo="Aprovadas"
                valor={aprovada}
                descricao="Validadas pelo auditor"
                destaque="success"
              />

              <StatCard
                titulo="Finalizadas"
                valor={finalizada}
                descricao="Processos encerrados"
                destaque="info"
              />
            </section>

            {/* =================================================
                CONFERÊNCIAS
            ================================================== */}

            <section className="mt-8 overflow-hidden rounded-2xl border border-line bg-white shadow-card">
              {/* Cabeçalho da tabela */}

              <div className="flex flex-col justify-between gap-3 border-b border-line px-6 py-5 sm:flex-row sm:items-center">
                <div>
                  <h2 className="text-lg font-semibold text-brand">
                    Minhas conferências
                  </h2>

                  <p className="mt-1 text-xs text-muted">
                    Conferências disponíveis para o usuário autenticado.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="rounded-lg border border-line bg-canvas px-3 py-1.5 text-xs font-medium text-ink">
                    {total} registro(s)
                  </span>
                </div>
              </div>

              {/* Estado vazio */}

              {conferencias.length === 0 ? (
                <div className="px-6 py-16 text-center">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-line bg-canvas text-muted">
                    <ClipboardIcon />
                  </div>

                  <p className="font-medium text-ink">
                    Nenhuma conferência encontrada
                  </p>

                  <p className="mx-auto mt-2 max-w-md text-sm text-muted">
                    Ainda não existem conferências vinculadas a este
                    estabelecimento.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead className="border-b border-line bg-canvas">
                      <tr>
                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          ID
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          Estabelecimento
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          Status
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          Data de início
                        </th>

                        <th className="px-6 py-4 text-right text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          Ação
                        </th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-line">
                      {conferencias.map((conferencia) => (
                        <tr
                          key={conferencia.id}
                          onClick={() =>
                            router.push(
                              `/dashboard/conferencia/${conferencia.id}`,
                            )
                          }
                          className="group cursor-pointer transition hover:bg-canvas"
                        >
                          <td className="px-6 py-4">
                            <span className="font-semibold text-brand">
                              #{conferencia.id}
                            </span>
                          </td>

                          <td className="px-6 py-4 text-muted">
                            {conferencia.estabelecimento_id}
                          </td>

                          <td className="px-6 py-4">
                            <StatusBadge status={conferencia.status} />
                          </td>

                          <td className="px-6 py-4 text-muted">
                            {formatarData(conferencia.data_inicio)}
                          </td>

                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={(event) => {
                                event.stopPropagation();

                                router.push(
                                  `/dashboard/conferencia/${conferencia.id}`,
                                );
                              }}
                              className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs font-semibold text-brand transition hover:border-brand-light hover:bg-canvas"
                            >
                              Abrir
                              <ArrowIcon />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}

/* ============================================================
   STAT CARD
============================================================ */

function StatCard({
  titulo,
  valor,
  descricao,
  destaque,
}: {
  titulo: string;
  valor: number;
  descricao: string;
  destaque: "default" | "warning" | "orange" | "info" | "success";
}) {
  const estilos = {
    default: {
      borda: "border-line",
      indicador: "bg-muted",
      numero: "text-ink",
    },

    warning: {
      borda: "border-warning/35",
      indicador: "bg-warning",
      numero: "text-warning-strong",
    },

    orange: {
      borda: "border-attention/35",
      indicador: "bg-attention",
      numero: "text-attention-strong",
    },

    info: {
      borda: "border-info/35",
      indicador: "bg-info",
      numero: "text-info",
    },

    success: {
      borda: "border-success/35",
      indicador: "bg-success",
      numero: "text-success-strong",
    },
  };

  const estilo = estilos[destaque];

  return (
    <div
      className={`rounded-2xl border ${estilo.borda} bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-md`}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          {titulo}
        </p>

        <span className={`h-2 w-2 rounded-full ${estilo.indicador}`} />
      </div>

      <p className={`mt-4 text-3xl font-bold tracking-tight ${estilo.numero}`}>
        {valor}
      </p>

      <p className="mt-2 text-xs text-muted">{descricao}</p>
    </div>
  );
}

/* ============================================================
   STATUS BADGE
============================================================ */

function StatusBadge({ status }: { status: string }) {
  const statusNormalizado = status.toUpperCase();

  let classes = "border-line bg-canvas text-muted";

  let indicador = "bg-muted";

  if (statusNormalizado === "RASCUNHO") {
    classes = "border-warning/30 bg-warning-soft text-warning-strong";

    indicador = "bg-warning";
  }

  if (statusNormalizado === "REABERTA") {
    classes = "border-attention/30 bg-attention-soft text-attention-strong";

    indicador = "bg-attention";
  }

  if (statusNormalizado === "APROVADA") {
    classes = "border-success/30 bg-success-soft text-success-strong";

    indicador = "bg-success";
  }

  if (statusNormalizado === "FINALIZADA") {
    classes = "border-info/30 bg-info-soft text-info";

    indicador = "bg-info";
  }

  if (statusNormalizado === "REPROVADA") {
    classes = "border-danger/30 bg-danger-soft text-danger";

    indicador = "bg-danger";
  }

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${classes}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${indicador}`} />

      {status}
    </span>
  );
}

/* ============================================================
   ÍCONES
============================================================ */

function DashboardIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="7" height="7" rx="1" />

      <rect x="14" y="3" width="7" height="7" rx="1" />

      <rect x="3" y="14" width="7" height="7" rx="1" />

      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}

function ClipboardIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="5" y="4" width="14" height="17" rx="2" />

      <path d="M9 4V2h6v2" />

      <path d="M9 10h6" />

      <path d="M9 14h6" />

      <path d="M9 18h3" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="5" y1="12" x2="19" y2="12" />

      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />

      <line x1="12" y1="8" x2="12" y2="12" />

      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}
