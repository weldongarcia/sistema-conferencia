"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  buscarConferencias,
  buscarUsuarioAtual,
} from "../../../services/api";

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

  useEffect(() => {
    async function carregar() {
      try {
        const token = localStorage.getItem("token");

        if (!token) {
          router.push("/");
          return;
        }

        const usuarioAtual = await buscarUsuarioAtual(token);

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
            : "Não foi possível carregar o painel do auditor."
        );
      } finally {
        setCarregando(false);
      }
    }

    carregar();
  }, [router]);

  function sair() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    localStorage.removeItem("perfil");

    router.push("/");
  }

  function abrirConferencia(id: number) {
    router.push(`/dashboard/conferencia/${id}`);
  }

  function formatarData(data: string) {
    return new Date(data).toLocaleString("pt-BR");
  }

  function contarStatus(status: string) {
    return conferencias.filter(
      (conferencia) =>
        conferencia.status.toUpperCase() === status
    ).length;
  }

  if (carregando) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-sm text-slate-400">
            Carregando painel de auditoria...
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
              Painel de auditoria
            </p>

          </div>

          <div className="flex items-center gap-5">

            <div className="text-right">

              <p className="text-sm font-semibold text-white">
                {usuario?.username}
              </p>

              <p className="text-xs text-emerald-400">
                AUDITOR
              </p>

            </div>

            <button
              onClick={sair}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
            >
              Sair
            </button>

          </div>

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
              Auditoria
            </div>

            <div className="rounded-lg px-4 py-3 text-sm text-slate-400">
              Conferências
            </div>

            <div className="rounded-lg px-4 py-3 text-sm text-slate-400">
              Divergências
            </div>

            <div className="rounded-lg px-4 py-3 text-sm text-slate-400">
              Histórico
            </div>

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

            <p className="text-sm font-medium text-emerald-400">
              AUDITOR
            </p>

            <h2 className="mt-1 text-3xl font-bold">
              Painel de Auditoria
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Visualização de todas as conferências do grupo.
            </p>

          </div>

          {/* =================================================
              ERRO
          ================================================== */}

          {erro && (
            <div className="mb-6 rounded-xl border border-red-900 bg-red-950/40 p-5">

              <p className="font-semibold text-red-300">
                Erro
              </p>

              <p className="mt-2 text-sm text-red-400">
                {erro}
              </p>

            </div>
          )}

          {/* =================================================
              INDICADORES
          ================================================== */}

          {!erro && (
            <>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">

                <Card
                  titulo="Total"
                  valor={conferencias.length}
                />

                <Card
                  titulo="Rascunhos"
                  valor={contarStatus("RASCUNHO")}
                />

                <Card
                  titulo="Reabertas"
                  valor={contarStatus("REABERTA")}
                />

                <Card
                  titulo="Finalizadas"
                  valor={contarStatus("FINALIZADA")}
                />

                <Card
                  titulo="Aprovadas"
                  valor={contarStatus("APROVADA")}
                />

                <Card
                  titulo="Reprovadas"
                  valor={contarStatus("REPROVADA")}
                />

              </div>

              {/* =============================================
                  LISTA DE CONFERÊNCIAS
              ============================================== */}

              <div className="mt-8 overflow-hidden rounded-xl border border-slate-800 bg-slate-900">

                <div className="flex flex-col justify-between gap-2 border-b border-slate-800 px-6 py-5 sm:flex-row sm:items-center">

                  <div>

                    <h3 className="font-semibold">
                      Todas as conferências
                    </h3>

                    <p className="mt-1 text-xs text-slate-500">
                      O auditor possui acesso às conferências de
                      todas as lojas.
                    </p>

                  </div>

                  <span className="text-xs text-slate-500">
                    {conferencias.length} registro(s)
                  </span>

                </div>

                {conferencias.length === 0 ? (

                  <div className="px-6 py-12 text-center">

                    <p className="font-medium text-slate-300">
                      Nenhuma conferência encontrada
                    </p>

                    <p className="mt-2 text-sm text-slate-500">
                      Ainda não existem conferências cadastradas.
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
                            Loja
                          </th>

                          <th className="px-6 py-4">
                            Usuário
                          </th>

                          <th className="px-6 py-4">
                            Status
                          </th>

                          <th className="px-6 py-4">
                            Data
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
                              abrirConferencia(
                                conferencia.id
                              )
                            }
                            className="cursor-pointer transition hover:bg-slate-800/50"
                          >

                            {/* ID */}

                            <td className="px-6 py-4 font-semibold">
                              #{conferencia.id}
                            </td>

                            {/* LOJA */}

                            <td className="px-6 py-4">

                              <span className="font-medium text-white">
                                {conferencia.estabelecimento_id}
                              </span>

                            </td>

                            {/* USUÁRIO */}

                            <td className="px-6 py-4 text-slate-400">
                              #{conferencia.usuario_id}
                            </td>

                            {/* STATUS */}

                            <td className="px-6 py-4">

                              <StatusBadge
                                status={conferencia.status}
                              />

                            </td>

                            {/* DATA */}

                            <td className="px-6 py-4 text-slate-400">
                              {formatarData(
                                conferencia.data_inicio
                              )}
                            </td>

                            {/* AÇÃO */}

                            <td className="px-6 py-4">

                              <button
                                onClick={(event) => {
                                  event.stopPropagation();

                                  abrirConferencia(
                                    conferencia.id
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
  const normalizado = status.toUpperCase();

  let classes = "bg-slate-800 text-slate-300";

  if (normalizado === "RASCUNHO") {
    classes = "bg-yellow-950 text-yellow-300";
  }

  if (normalizado === "REABERTA") {
    classes = "bg-orange-950 text-orange-300";
  }

  if (normalizado === "FINALIZADA") {
    classes = "bg-emerald-950 text-emerald-300";
  }

  if (normalizado === "APROVADA") {
    classes = "bg-blue-950 text-blue-300";
  }

  if (normalizado === "REPROVADA") {
    classes = "bg-red-950 text-red-300";
  }

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${classes}`}
    >
      {status}
    </span>
  );
}