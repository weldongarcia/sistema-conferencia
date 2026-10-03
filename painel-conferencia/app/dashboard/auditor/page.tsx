"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CircleAlert, LayoutGrid, ShieldCheck } from "lucide-react";

import AppShell from "../../../components/layout/AppShell";

import { buscarConferencias, buscarUsuarioAtual } from "../../../services/api";

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

export default function AuditorDashboardPage() {
  const router = useRouter();

  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [conferencias, setConferencias] = useState<Conferencia[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  /* ==========================================================
     CARREGAMENTO
  ========================================================== */

  useEffect(() => {
    async function carregar() {
      try {
        const token = localStorage.getItem("token");

        if (!token) {
          router.push("/login");
          return;
        }

        const usuarioAtual = await buscarUsuarioAtual(token);

        /* ================================================
           PROTEÇÃO DE PERFIL
        ================================================= */

        if (usuarioAtual.perfil !== "AUDITOR") {
          router.push("/dashboard");
          return;
        }

        const dados = await buscarConferencias(token);

        setUsuario(usuarioAtual);
        setConferencias(dados);
      } catch (error) {
        console.error(error);

        setErro(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar o painel do auditor.",
        );
      } finally {
        setCarregando(false);
      }
    }

    carregar();
  }, [router]);

  /* ==========================================================
     LOGOUT
  ========================================================== */

  function sair() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    localStorage.removeItem("perfil");

    router.push("/login");
  }

  /* ==========================================================
     ABRIR CONFERÊNCIA
  ========================================================== */

  function abrirConferencia(id: number) {
    router.push(`/dashboard/conferencia/${id}`);
  }

  /* ==========================================================
     FORMATAÇÃO
  ========================================================== */

  function formatarData(data: string) {
    return new Date(data).toLocaleString("pt-BR");
  }

  /* ==========================================================
     CONTAGEM POR STATUS
  ========================================================== */

  function contarStatus(status: string) {
    return conferencias.filter(
      (conferencia) => conferencia.status.toUpperCase() === status,
    ).length;
  }

  /* ==========================================================
     LOADING
  ========================================================== */

  if (carregando) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas text-ink">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-line border-t-brand-light" />

          <p className="text-sm text-muted">
            Carregando painel de auditoria...
          </p>
        </div>
      </main>
    );
  }

  /* ==========================================================
     MENU DO AUDITOR
  ========================================================== */

  const menuItems = [
    {
      label: "Dashboard",
      href: "/dashboard",
      activeKey: "dashboard",
      icon: <LayoutGrid size={18} strokeWidth={1.8} />,
    },
    {
      label: "Conferências",
      href: "/dashboard/auditor",
      activeKey: "conferencias",
      icon: <ClipboardIcon />,
    },
    {
      label: "Auditoria",
      href: "/dashboard/auditor",
      activeKey: "auditoria",
      icon: <ShieldCheck size={18} strokeWidth={1.8} />,
    },
  ];

  /* ==========================================================
     INDICADORES
  ========================================================== */

  const total = conferencias.length;

  const rascunho = contarStatus("RASCUNHO");

  const reaberta = contarStatus("REABERTA");

  const finalizada = contarStatus("FINALIZADA");

  const aprovada = contarStatus("APROVADA");

  const reprovada = contarStatus("REPROVADA");

  /* ==========================================================
     RENDER
  ========================================================== */

  return (
    <AppShell
      usuario={usuario?.username}
      perfil="AUDITOR"
      menuItems={menuItems}
      activeKey="auditoria"
      onLogout={sair}
    >
      <div className="mx-auto w-full max-w-[1500px] p-5 sm:p-8">
        {/* ====================================================
            CABEÇALHO
        ===================================================== */}

        <section className="mb-8">
          <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-info" />

                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-info">
                  Auditoria
                </p>
              </div>

              <h1 className="text-3xl font-bold tracking-tight text-brand sm:text-4xl">
                Painel de Auditoria
              </h1>

              <p className="mt-2 text-sm text-muted">
                Visualização e acompanhamento das conferências do grupo.
              </p>
            </div>

            <div className="rounded-xl border border-line bg-white px-5 py-3 shadow-card">
              <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted">
                Acesso
              </p>

              <div className="mt-1 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-info" />

                <p className="text-sm font-semibold text-brand">Auditor</p>
              </div>
            </div>
          </div>
        </section>

        {/* ====================================================
            ERRO
        ===================================================== */}

        {erro && (
          <div className="mb-6 rounded-xl border border-danger/30 bg-danger-soft p-5">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-danger">
                <CircleAlert size={19} />
              </div>

              <div>
                <p className="font-semibold text-danger">
                  Erro ao carregar o painel
                </p>

                <p className="mt-1 text-sm text-danger">{erro}</p>
              </div>
            </div>
          </div>
        )}

        {/* ====================================================
            CONTEÚDO
        ===================================================== */}

        {!erro && (
          <>
            {/* ==================================================
                INDICADORES
            =================================================== */}

            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
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
                titulo="Finalizadas"
                valor={finalizada}
                descricao="Aguardando análise"
                destaque="info"
              />

              <StatCard
                titulo="Aprovadas"
                valor={aprovada}
                descricao="Validadas"
                destaque="success"
              />

              <StatCard
                titulo="Reprovadas"
                valor={reprovada}
                descricao="Necessitam revisão"
                destaque="danger"
              />
            </section>

            {/* ==================================================
                LISTA
            =================================================== */}

            <section className="mt-8 overflow-hidden rounded-2xl border border-line bg-white shadow-card">
              {/* Cabeçalho */}

              <div className="flex flex-col justify-between gap-3 border-b border-line px-6 py-5 sm:flex-row sm:items-center">
                <div>
                  <h2 className="text-lg font-semibold text-brand">
                    Todas as conferências
                  </h2>

                  <p className="mt-1 text-xs text-muted">
                    O auditor possui acesso às conferências de todas as lojas.
                  </p>
                </div>

                <span className="rounded-lg border border-line bg-canvas px-3 py-1.5 text-xs font-semibold text-ink">
                  {total} registro(s)
                </span>
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
                    Ainda não existem conferências cadastradas.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[900px] text-left text-sm">
                    <thead className="border-b border-line bg-canvas">
                      <tr>
                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          ID
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          Loja
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                          Usuário
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
                          onClick={() => abrirConferencia(conferencia.id)}
                          className="group cursor-pointer transition hover:bg-canvas"
                        >
                          {/* ID */}

                          <td className="px-6 py-4">
                            <span className="font-semibold text-brand">
                              #{conferencia.id}
                            </span>
                          </td>

                          {/* LOJA */}

                          <td className="px-6 py-4">
                            <span className="font-medium text-ink">
                              {conferencia.estabelecimento_id}
                            </span>
                          </td>

                          {/* USUÁRIO */}

                          <td className="px-6 py-4 text-muted">
                            #{conferencia.usuario_id}
                          </td>

                          {/* STATUS */}

                          <td className="px-6 py-4">
                            <StatusBadge status={conferencia.status} />
                          </td>

                          {/* DATA */}

                          <td className="px-6 py-4 text-muted">
                            {formatarData(conferencia.data_inicio)}
                          </td>

                          {/* AÇÃO */}

                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={(event) => {
                                event.stopPropagation();

                                abrirConferencia(conferencia.id);
                              }}
                              className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs font-semibold text-brand transition hover:border-brand-light hover:bg-canvas"
                            >
                              Abrir
                              <ArrowRight size={15} />
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
  destaque: "default" | "warning" | "orange" | "success" | "danger" | "info";
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
      numero: "text-warning",
    },

    orange: {
      borda: "border-attention/35",
      indicador: "bg-attention",
      numero: "text-attention",
    },

    success: {
      borda: "border-success/35",
      indicador: "bg-success",
      numero: "text-success",
    },

    danger: {
      borda: "border-danger/35",
      indicador: "bg-danger",
      numero: "text-danger",
    },

    info: {
      borda: "border-info/35",
      indicador: "bg-info",
      numero: "text-info",
    },
  };

  const estilo = estilos[destaque];

  return (
    <div
      className={[
        "rounded-2xl border bg-white p-5",
        "shadow-card",
        "transition duration-200",
        "hover:-translate-y-0.5 hover:shadow-md",
        estilo.borda,
      ].join(" ")}
    >
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
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
  const normalizado = status.toUpperCase();

  let classes = "border-line bg-canvas text-muted";

  let indicador = "bg-muted";

  if (normalizado === "RASCUNHO") {
    classes = "border-warning/30 bg-warning-soft text-warning-strong";

    indicador = "bg-warning";
  }

  if (normalizado === "REABERTA") {
    classes = "border-attention/30 bg-attention-soft text-attention-strong";

    indicador = "bg-attention";
  }

  if (normalizado === "FINALIZADA") {
    classes = "border-info/30 bg-info-soft text-info";

    indicador = "bg-info";
  }

  if (normalizado === "APROVADA") {
    classes = "border-success/30 bg-success-soft text-success-strong";

    indicador = "bg-success";
  }

  if (normalizado === "REPROVADA") {
    classes = "border-danger/30 bg-danger-soft text-danger";

    indicador = "bg-danger";
  }

  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-full border",
        "px-3 py-1.5 text-xs font-semibold",
        classes,
      ].join(" ")}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${indicador}`} />

      {status}
    </span>
  );
}

/* ============================================================
   ÍCONES
============================================================ */

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
