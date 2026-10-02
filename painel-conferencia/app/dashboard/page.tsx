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
      <main className="flex min-h-screen items-center justify-center bg-[#F6F7F5] text-[#17231D]">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-[#DCE4DF] border-t-[#176B4D]" />

          <p className="text-sm text-[#64736B]">Carregando painel...</p>
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
                <span className="h-2 w-2 rounded-full bg-[#176B4D]" />

                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#176B4D]">
                  {usuario?.perfil || "Usuário"}
                </p>
              </div>

              <h1 className="text-3xl font-bold tracking-tight text-[#0B3D2E] sm:text-4xl">
                Dashboard
              </h1>

              <p className="mt-2 text-sm text-[#64736B]">
                Acompanhe as conferências do seu estabelecimento.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="rounded-xl border border-[#DCE4DF] bg-white px-4 py-3 shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
                <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-[#64736B]">
                  Estabelecimento
                </p>

                <p className="mt-1 text-sm font-semibold text-[#17231D]">
                  {nomeEstabelecimento()}
                </p>
              </div>

              <button
                onClick={novaConferencia}
                disabled={carregando}
                className="inline-flex h-[46px] items-center justify-center gap-2 rounded-xl bg-[#0B3D2E] px-5 text-sm font-semibold text-white shadow-[0_1px_2px_rgba(23,35,29,0.12)] transition hover:bg-[#176B4D] disabled:cursor-not-allowed disabled:opacity-50"
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
          <div className="mb-6 rounded-xl border border-[#D64545]/30 bg-[#FFF5F5] p-5">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-[#D64545]">
                <AlertIcon />
              </div>

              <div>
                <p className="font-semibold text-[#D64545]">
                  Erro ao carregar o Dashboard
                </p>

                <p className="mt-1 text-sm text-[#D64545]">{erro}</p>
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

            <section className="mt-8 overflow-hidden rounded-2xl border border-[#DCE4DF] bg-white shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
              {/* Cabeçalho da tabela */}

              <div className="flex flex-col justify-between gap-3 border-b border-[#DCE4DF] px-6 py-5 sm:flex-row sm:items-center">
                <div>
                  <h2 className="text-lg font-semibold text-[#0B3D2E]">
                    Minhas conferências
                  </h2>

                  <p className="mt-1 text-xs text-[#64736B]">
                    Conferências disponíveis para o usuário autenticado.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="rounded-lg border border-[#DCE4DF] bg-[#F6F7F5] px-3 py-1.5 text-xs font-medium text-[#17231D]">
                    {total} registro(s)
                  </span>
                </div>
              </div>

              {/* Estado vazio */}

              {conferencias.length === 0 ? (
                <div className="px-6 py-16 text-center">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B]">
                    <ClipboardIcon />
                  </div>

                  <p className="font-medium text-[#17231D]">
                    Nenhuma conferência encontrada
                  </p>

                  <p className="mx-auto mt-2 max-w-md text-sm text-[#64736B]">
                    Ainda não existem conferências vinculadas a este
                    estabelecimento.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead className="border-b border-[#DCE4DF] bg-[#F6F7F5]">
                      <tr>
                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64736B]">
                          ID
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64736B]">
                          Estabelecimento
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64736B]">
                          Status
                        </th>

                        <th className="px-6 py-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64736B]">
                          Data de início
                        </th>

                        <th className="px-6 py-4 text-right text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64736B]">
                          Ação
                        </th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-[#DCE4DF]">
                      {conferencias.map((conferencia) => (
                        <tr
                          key={conferencia.id}
                          onClick={() =>
                            router.push(
                              `/dashboard/conferencia/${conferencia.id}`,
                            )
                          }
                          className="group cursor-pointer transition hover:bg-[#F6F7F5]"
                        >
                          <td className="px-6 py-4">
                            <span className="font-semibold text-[#0B3D2E]">
                              #{conferencia.id}
                            </span>
                          </td>

                          <td className="px-6 py-4 text-[#64736B]">
                            {conferencia.estabelecimento_id}
                          </td>

                          <td className="px-6 py-4">
                            <StatusBadge status={conferencia.status} />
                          </td>

                          <td className="px-6 py-4 text-[#64736B]">
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
                              className="inline-flex items-center gap-2 rounded-lg border border-[#DCE4DF] px-3 py-2 text-xs font-semibold text-[#0B3D2E] transition hover:border-[#176B4D] hover:bg-[#F6F7F5]"
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
      borda: "border-[#DCE4DF]",
      indicador: "bg-[#64736B]",
      numero: "text-[#17231D]",
    },

    warning: {
      borda: "border-[#D99000]/35",
      indicador: "bg-[#D99000]",
      numero: "text-[#A86F00]",
    },

    orange: {
      borda: "border-[#E87524]/35",
      indicador: "bg-[#E87524]",
      numero: "text-[#C95F16]",
    },

    info: {
      borda: "border-[#3578B8]/35",
      indicador: "bg-[#3578B8]",
      numero: "text-[#3578B8]",
    },

    success: {
      borda: "border-[#1DB954]/35",
      indicador: "bg-[#1DB954]",
      numero: "text-[#168C40]",
    },
  };

  const estilo = estilos[destaque];

  return (
    <div
      className={`rounded-2xl border ${estilo.borda} bg-white p-5 shadow-[0_1px_2px_rgba(23,35,29,0.04)] transition hover:-translate-y-0.5 hover:shadow-md`}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#64736B]">
          {titulo}
        </p>

        <span className={`h-2 w-2 rounded-full ${estilo.indicador}`} />
      </div>

      <p className={`mt-4 text-3xl font-bold tracking-tight ${estilo.numero}`}>
        {valor}
      </p>

      <p className="mt-2 text-xs text-[#64736B]">{descricao}</p>
    </div>
  );
}

/* ============================================================
   STATUS BADGE
============================================================ */

function StatusBadge({ status }: { status: string }) {
  const statusNormalizado = status.toUpperCase();

  let classes = "border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B]";

  let indicador = "bg-[#64736B]";

  if (statusNormalizado === "RASCUNHO") {
    classes = "border-[#D99000]/30 bg-[#FFF8E8] text-[#A86F00]";

    indicador = "bg-[#D99000]";
  }

  if (statusNormalizado === "REABERTA") {
    classes = "border-[#E87524]/30 bg-[#FFF3EA] text-[#C95F16]";

    indicador = "bg-[#E87524]";
  }

  if (statusNormalizado === "APROVADA") {
    classes = "border-[#1DB954]/30 bg-[#EFFAF3] text-[#168C40]";

    indicador = "bg-[#1DB954]";
  }

  if (statusNormalizado === "FINALIZADA") {
    classes = "border-[#3578B8]/30 bg-[#EEF5FB] text-[#3578B8]";

    indicador = "bg-[#3578B8]";
  }

  if (statusNormalizado === "REPROVADA") {
    classes = "border-[#D64545]/30 bg-[#FFF5F5] text-[#D64545]";

    indicador = "bg-[#D64545]";
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
