"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CircleAlert } from "lucide-react";
import AppShell from "../../components/layout/AppShell";
import { MENU_CONFERENCIAS, menuPorPerfil } from "../../components/layout/menu";
import ClipboardIcon from "../../components/ui/ClipboardIcon";
import EmptyState from "../../components/ui/EmptyState";
import PageLoading from "../../components/ui/PageLoading";
import StatusBadge from "../../components/ui/StatusBadge";

import {
  buscarConferencias,
  buscarUsuarioAtual,
  criarConferencia,
} from "../../services/api";
import { limparSessao, tratarSessaoExpirada } from "../../services/sessao";

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

        const dadosUsuario = await buscarUsuarioAtual(token);

        /* ================================================
           PROTEÇÃO DE PERFIL
           Auditor possui painel próprio.
        ================================================= */

        if (dadosUsuario.perfil === "AUDITOR") {
          router.replace("/dashboard/auditor");
          return;
        }

        const dadosConferencias = await buscarConferencias(token);

        setUsuario(dadosUsuario);
        setConferencias(dadosConferencias);
      } catch (error) {
        if (tratarSessaoExpirada(error, router)) return;

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
      if (tratarSessaoExpirada(error, router)) return;

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
    limparSessao();

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

  if (carregando) {
    return <PageLoading mensagem="Carregando painel..." />;
  }

  return (
    <AppShell
      usuario={usuario?.username}
      perfil={usuario?.perfil}
      menuItems={menuPorPerfil(usuario?.perfil)}
      activeKey={MENU_CONFERENCIAS}
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
                <CircleAlert size={19} />
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
                  <EmptyState
                    icone={<ClipboardIcon />}
                    titulo="Nenhuma conferência encontrada"
                    descricao="Ainda não existem conferências vinculadas a este estabelecimento."
                  />
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
