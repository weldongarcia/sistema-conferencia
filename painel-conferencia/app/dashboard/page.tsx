"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
          router.push("/");
          return;
        }

        const [dadosUsuario, dadosConferencias] =
          await Promise.all([
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
            : "Não foi possível carregar o Dashboard."
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
      (conferencia) =>
        conferencia.status.toUpperCase() === status
    ).length;
  }

  async function novaConferencia() {
    if (carregando) return;

    try {
      setCarregando(true);
      setErro("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/");
        return;
      }

      const conferencia = await criarConferencia(token);

      router.push(
        `/dashboard/conferencia/${conferencia.id}`
      );
    } catch (error) {
      console.error(error);

      setErro(
        error instanceof Error
          ? error.message
          : "Não foi possível criar a conferência."
      );

      setCarregando(false);
    }
  }

  function sair() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");

    router.push("/");
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
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-sm text-slate-400">
            Carregando painel...
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">

      {/* =====================================================
          TOPO
      ====================================================== */}

      <header className="border-b border-slate-800 bg-slate-900">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">

          <div>
            <h1 className="text-xl font-bold">
              Sistema de Conferência
            </h1>

            <p className="text-xs text-slate-400">
              Painel operacional
            </p>
          </div>

          {usuario && (
            <div className="flex items-center gap-5">

              <div className="text-right">
                <p className="text-sm font-semibold text-white">
                  {usuario.username}
                </p>

                <p className="text-xs text-slate-400">
                  {usuario.perfil}
                </p>
              </div>

              <button
                onClick={sair}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
              >
                Sair
              </button>

            </div>
          )}

        </div>
      </header>

      {/* =====================================================
          LAYOUT
      ====================================================== */}

      <div className="mx-auto flex max-w-7xl">

        {/* ===================================================
            MENU
        ==================================================== */}

        <aside className="hidden min-h-[calc(100vh-73px)] w-60 border-r border-slate-800 bg-slate-900 p-4 md:block">

          <nav className="space-y-2">

            <div className="rounded-lg bg-emerald-900/40 px-4 py-3 text-sm font-medium text-emerald-300">
              Dashboard
            </div>

            <div className="rounded-lg px-4 py-3 text-sm text-slate-400">
              Conferências
            </div>

            {usuario?.perfil === "AUDITOR" && (
              <>
                <div className="rounded-lg px-4 py-3 text-sm text-slate-400">
                  Divergências
                </div>

                <div className="rounded-lg px-4 py-3 text-sm text-slate-400">
                  Auditoria
                </div>
              </>
            )}

          </nav>

        </aside>

        {/* ===================================================
            PRINCIPAL
        ==================================================== */}

        <section className="flex-1 p-6">

          {/* =================================================
              CABEÇALHO
          ================================================== */}

          <div className="mb-8">

            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">

              <div>

                <p className="text-sm font-medium text-emerald-400">
                  {usuario?.perfil}
                </p>

                <h2 className="mt-1 text-3xl font-bold">
                  Dashboard
                </h2>

                <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">

                  <p className="text-sm text-slate-400">
                    {nomeEstabelecimento()}
                  </p>

                  <button
                    onClick={novaConferencia}
                    disabled={carregando}
                    className="inline-flex items-center justify-center rounded-xl bg-emerald-800 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {carregando
                      ? "Criando..."
                      : "+ Nova Conferência"}
                  </button>

                </div>

              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 px-5 py-3">

                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Usuário
                </p>

                <p className="mt-1 font-semibold">
                  {usuario?.username}
                </p>

              </div>

            </div>

          </div>

          {/* =================================================
              ERRO
          ================================================== */}

          {erro && (
            <div className="mb-6 rounded-xl border border-red-900 bg-red-950/40 p-5 text-red-300">

              <p className="font-semibold">
                Erro ao carregar o Dashboard
              </p>

              <p className="mt-2 text-sm">
                {erro}
              </p>

            </div>
          )}

          {/* =================================================
              CARDS
          ================================================== */}

          {!erro && (
            <>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">

                <Card
                  titulo="Total"
                  valor={total}
                />

                <Card
                  titulo="Rascunhos"
                  valor={rascunho}
                />

                <Card
                  titulo="Reabertas"
                  valor={reaberta}
                />

                <Card
                  titulo="Aprovadas"
                  valor={aprovada}
                />

                <Card
                  titulo="Finalizadas"
                  valor={finalizada}
                />

              </div>

              {/* =============================================
                  CONFERÊNCIAS
              ============================================== */}

              <div className="mt-8 overflow-hidden rounded-xl border border-slate-800 bg-slate-900">

                <div className="flex flex-col justify-between gap-2 border-b border-slate-800 px-6 py-5 sm:flex-row sm:items-center">

                  <div>

                    <h3 className="font-semibold">
                      Minhas conferências
                    </h3>

                    <p className="mt-1 text-xs text-slate-500">
                      Conferências disponíveis para o usuário autenticado.
                    </p>

                  </div>

                  <span className="text-xs text-slate-500">
                    {total} registro(s)
                  </span>

                </div>

                {conferencias.length === 0 ? (

                  <div className="px-6 py-12 text-center">

                    <p className="font-medium text-slate-300">
                      Nenhuma conferência encontrada
                    </p>

                    <p className="mt-2 text-sm text-slate-500">
                      Ainda não existem conferências vinculadas a este estabelecimento.
                    </p>

                  </div>

                ) : (

                  <div className="overflow-x-auto">

                    <table className="w-full text-left text-sm">

                      <thead className="bg-slate-950 text-xs uppercase text-slate-500">

                        <tr>

                          <th className="px-6 py-4">
                            ID
                          </th>

                          <th className="px-6 py-4">
                            Estabelecimento
                          </th>

                          <th className="px-6 py-4">
                            Status
                          </th>

                          <th className="px-6 py-4">
                            Data de início
                          </th>

                          <th className="px-6 py-4">
                            Ação
                          </th>

                        </tr>

                      </thead>

                      <tbody className="divide-y divide-slate-800">

                        {conferencias.map((conferencia) => (

                          <tr
                            key={conferencia.id}
                            onClick={() =>
                              router.push(
                                `/dashboard/conferencia/${conferencia.id}`
                              )
                            }
                            className="cursor-pointer transition hover:bg-slate-800/50"
                          >

                            <td className="px-6 py-4 font-semibold">
                              #{conferencia.id}
                            </td>

                            <td className="px-6 py-4 text-slate-300">
                              {conferencia.estabelecimento_id}
                            </td>

                            <td className="px-6 py-4">
                              <StatusBadge
                                status={conferencia.status}
                              />
                            </td>

                            <td className="px-6 py-4 text-slate-400">
                              {formatarData(
                                conferencia.data_inicio
                              )}
                            </td>

                            <td className="px-6 py-4">

                              <button
                                onClick={(event) => {
                                  event.stopPropagation();

                                  router.push(
                                    `/dashboard/conferencia/${conferencia.id}`
                                  );
                                }}
                                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-emerald-700 hover:bg-emerald-900/20 hover:text-emerald-300"
                              >
                                Abrir
                              </button>

                            </td>

                          </tr>

                        ))}

                      </tbody>

                    </table>

                  </div>

                )}

              </div>

            </>
          )}

        </section>

      </div>

    </main>
  );
}


/* ============================================================
   CARD
============================================================ */

function Card({
  titulo,
  valor,
}: {
  titulo: string;
  valor: number;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">

      <p className="text-sm text-slate-400">
        {titulo}
      </p>

      <p className="mt-2 text-3xl font-bold">
        {valor}
      </p>

    </div>
  );
}


/* ============================================================
   STATUS
============================================================ */

function StatusBadge({
  status,
}: {
  status: string;
}) {
  const statusNormalizado = status.toUpperCase();

  let classes = "bg-slate-800 text-slate-300";

  if (statusNormalizado === "RASCUNHO") {
    classes = "bg-yellow-950 text-yellow-300";
  }

  if (statusNormalizado === "REABERTA") {
    classes = "bg-orange-950 text-orange-300";
  }

  if (statusNormalizado === "APROVADA") {
    classes = "bg-blue-950 text-blue-300";
  }

  if (statusNormalizado === "FINALIZADA") {
    classes = "bg-emerald-950 text-emerald-300";
  }

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${classes}`}
    >
      {status}
    </span>
  );
}