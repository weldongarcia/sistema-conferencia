"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import {
  buscarConferencia,
  buscarTimelineConferencia,
  buscarUsuarioAtual,
  fecharConferencia,
  aprovarConferencia,
  reprovarConferencia,
  reabrirConferencia,
  justificarDivergencia,
} from "../../../../services/api";

type Usuario = {
  id: number;
  username?: string;
  perfil: string;
  estabelecimento_id?: number | null;
};

type ItemConferencia = {
  codigo: string;
  descricao: string | null;
  xml: number;
  contado: number;
  diferenca: number;
  divergente: boolean;
  divergencia_id: number | null;
  tipo_divergencia: string | null;
  justificado: boolean;
  justificativa_tipo: string | null;
  justificativa_descricao: string | null;
};

type DadosConferencia = {
  status: string;
  status_conferencia: string;
  total_itens: number;
  divergentes: number;
  versao: number;
  itens: ItemConferencia[];
};

type EventoTimeline = {
  data?: string;
  usuario?: string | null;
  evento?: string;
  acao?: string;
  versao?: number;
  motivo?: string | null;
};

const TIPOS_JUSTIFICATIVA = [
  {
    valor: "ERRO_FORNECEDOR",
    label: "Erro do fornecedor",
  },
  {
    valor: "ERRO_CONFERENCIA",
    label: "Erro de conferência",
  },
  {
    valor: "ERRO_CADASTRO",
    label: "Erro de cadastro",
  },
  {
    valor: "OUTROS",
    label: "Outros",
  },
];

export default function ConferenciaDetalhePage() {
  const params = useParams();
  const router = useRouter();

  const [dados, setDados] =
    useState<DadosConferencia | null>(null);

  const [usuario, setUsuario] =
    useState<Usuario | null>(null);

  const [timeline, setTimeline] =
    useState<EventoTimeline[]>([]);

  const [carregando, setCarregando] =
    useState(true);

  const [erro, setErro] =
    useState("");

  const [erroFechamento, setErroFechamento] =
    useState("");

  const [erroAuditoria, setErroAuditoria] =
    useState("");

  const [processandoAuditoria, setProcessandoAuditoria] =
    useState(false);

  const [fechando, setFechando] =
    useState(false);

  const [abrirReabertura, setAbrirReabertura] =
    useState(false);

  const [motivoReabertura, setMotivoReabertura] =
    useState("");

  const [justificativaAberta, setJustificativaAberta] =
    useState<number | null>(null);

  const [justificativaTipo, setJustificativaTipo] =
    useState("");

  const [justificativaDescricao, setJustificativaDescricao] =
    useState("");

  const [processandoJustificativa, setProcessandoJustificativa] =
    useState(false);

  const [erroJustificativa, setErroJustificativa] =
    useState("");

  const conferenciaId = Number(params.id);

  useEffect(() => {
    async function carregar() {
      try {
        const token = localStorage.getItem("token");

        if (!token) {
          router.push("/");
          return;
        }

        if (!conferenciaId) {
          throw new Error(
            "ID da conferência inválido."
          );
        }

        const [
          usuarioAtual,
          resultado,
          timelineAtualizada,
        ] = await Promise.all([
          buscarUsuarioAtual(token),
          buscarConferencia(
            token,
            conferenciaId
          ),
          buscarTimelineConferencia(
            token,
            conferenciaId
          ),
        ]);

        setUsuario(usuarioAtual);
        setDados(resultado);
        setTimeline(
          Array.isArray(timelineAtualizada)
            ? timelineAtualizada
            : []
        );
      } catch (error) {
        console.error(error);

        setErro(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar a conferência."
        );
      } finally {
        setCarregando(false);
      }
    }

    carregar();
  }, [conferenciaId, router]);

  function voltar() {
    if (usuario?.perfil === "AUDITOR") {
      router.push("/dashboard/auditor");
    } else {
      router.push("/dashboard");
    }
  }

  async function atualizarDados() {
    const token = localStorage.getItem("token");

    if (!token) {
      router.push("/");
      return;
    }

    const [
      atualizado,
      timelineAtualizada,
    ] = await Promise.all([
      buscarConferencia(
        token,
        conferenciaId
      ),
      buscarTimelineConferencia(
        token,
        conferenciaId
      ),
    ]);

    setDados(atualizado);

    setTimeline(
      Array.isArray(timelineAtualizada)
        ? timelineAtualizada
        : []
    );
  }

  async function fechar() {
    if (fechando) return;

    const confirmar = window.confirm(
      "Deseja realmente fechar esta conferência?\n\n" +
        "Após o fechamento, ela será encaminhada para o fluxo de auditoria."
    );

    if (!confirmar) return;

    try {
      setFechando(true);
      setErroFechamento("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/");
        return;
      }

      await fecharConferencia(
        token,
        conferenciaId
      );

      await atualizarDados();
    } catch (error) {
      console.error(error);

      setErroFechamento(
        error instanceof Error
          ? error.message
          : "Não foi possível fechar a conferência."
      );
    } finally {
      setFechando(false);
    }
  }

  async function aprovar() {
    if (processandoAuditoria) return;

    const confirmar = window.confirm(
      "Deseja aprovar esta conferência?\n\n" +
        "Após a aprovação, ela será considerada aprovada pela auditoria."
    );

    if (!confirmar) return;

    try {
      setProcessandoAuditoria(true);
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/");
        return;
      }

      await aprovarConferencia(
        token,
        conferenciaId
      );

      await atualizarDados();
    } catch (error) {
      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível aprovar a conferência."
      );
    } finally {
      setProcessandoAuditoria(false);
    }
  }

  async function reprovar() {
    if (processandoAuditoria) return;

    const confirmar = window.confirm(
      "Deseja reprovar esta conferência?\n\n" +
        "A conferência será marcada como REPROVADA."
    );

    if (!confirmar) return;

    try {
      setProcessandoAuditoria(true);
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/");
        return;
      }

      await reprovarConferencia(
        token,
        conferenciaId
      );

      await atualizarDados();
    } catch (error) {
      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível reprovar a conferência."
      );
    } finally {
      setProcessandoAuditoria(false);
    }
  }

  async function reabrir() {
    if (processandoAuditoria) return;

    const motivo = motivoReabertura.trim();

    if (!motivo) {
      setErroAuditoria(
        "Informe o motivo da reabertura."
      );
      return;
    }

    try {
      setProcessandoAuditoria(true);
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/");
        return;
      }

      await reabrirConferencia(
        token,
        conferenciaId,
        motivo
      );

      setMotivoReabertura("");
      setAbrirReabertura(false);

      await atualizarDados();
    } catch (error) {
      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível reabrir a conferência."
      );
    } finally {
      setProcessandoAuditoria(false);
    }
  }

  function abrirJustificativa(
    item: ItemConferencia
  ) {
    setJustificativaAberta(
      item.divergencia_id
    );

    setJustificativaTipo(
      item.justificativa_tipo || ""
    );

    setJustificativaDescricao(
      item.justificativa_descricao || ""
    );

    setErroJustificativa("");
  }

  function cancelarJustificativa() {
    setJustificativaAberta(null);
    setJustificativaTipo("");
    setJustificativaDescricao("");
    setErroJustificativa("");
  }

  async function justificar(item: ItemConferencia) {
    if (processandoJustificativa) return;

    if (!item.divergencia_id) {
      setErroJustificativa(
        "Divergência inválida."
      );
      return;
    }

    if (!justificativaTipo) {
      setErroJustificativa(
        "Selecione o tipo da justificativa."
      );
      return;
    }

    if (!justificativaDescricao.trim()) {
      setErroJustificativa(
        "Informe a descrição da justificativa."
      );
      return;
    }

    try {
      setProcessandoJustificativa(true);
      setErroJustificativa("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/");
        return;
      }

      await justificarDivergencia(
        token,
        item.divergencia_id,
        justificativaTipo,
        justificativaDescricao.trim()
      );

      cancelarJustificativa();

      await atualizarDados();
    } catch (error) {
      console.error(error);

      setErroJustificativa(
        error instanceof Error
          ? error.message
          : "Não foi possível justificar a divergência."
      );
    } finally {
      setProcessandoJustificativa(false);
    }
  }

  function formatarTipo(
    tipo: string | null
  ) {
    if (!tipo) return "-";

    return tipo
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(
        /\b\w/g,
        (letra) => letra.toUpperCase()
      );
  }

  function classeStatus(
    status: string
  ) {
    const normalizado =
      status.toUpperCase();

    if (normalizado === "APROVADA") {
      return "bg-blue-950 text-blue-300";
    }

    if (normalizado === "FINALIZADA") {
      return "bg-emerald-950 text-emerald-300";
    }

    if (normalizado === "REABERTA") {
      return "bg-orange-950 text-orange-300";
    }

    if (normalizado === "RASCUNHO") {
      return "bg-yellow-950 text-yellow-300";
    }

    if (normalizado === "REPROVADA") {
      return "bg-red-950 text-red-300";
    }

    return "bg-slate-800 text-slate-300";
  }

  if (carregando) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-slate-400">
            Carregando conferência...
          </p>
        </div>
      </main>
    );
  }

  if (erro || !dados) {
    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <div className="mx-auto max-w-3xl px-6 py-12">
          <div className="rounded-xl border border-red-900 bg-red-950/40 p-6">
            <h1 className="text-lg font-semibold text-red-300">
              Não foi possível carregar a conferência
            </h1>

            <p className="mt-2 text-sm text-red-400">
              {erro || "Nenhum dado encontrado."}
            </p>

            <button
              onClick={voltar}
              className="mt-5 rounded-lg bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
            >
              Voltar
            </button>
          </div>
        </div>
      </main>
    );
  }

  const statusAtual =
    dados.status_conferencia.toUpperCase();

  const ehAuditor =
    usuario?.perfil === "AUDITOR";

  const ehConferente =
    usuario?.perfil === "CONFERENTE";

  const podeJustificar =
    ehConferente &&
    (
      statusAtual === "RASCUNHO" ||
      statusAtual === "REABERTA"
    );

  const podeFechar =
    ehConferente &&
    (
      statusAtual === "RASCUNHO" ||
      statusAtual === "REABERTA"
    );

  const podeAuditar =
    ehAuditor &&
    statusAtual === "FINALIZADA";

  const podeReabrir =
    ehAuditor &&
    (
      statusAtual === "FINALIZADA" ||
      statusAtual === "REPROVADA"
    );

  const conferidos =
    dados.itens.filter(
      (item) => item.contado > 0
    ).length;

  const corretos =
    dados.itens.filter(
      (item) =>
        item.contado > 0 &&
        !item.divergente
    ).length;

  const percentual =
    dados.total_itens > 0
      ? Math.round(
          (conferidos /
            dados.total_itens) *
            100
        )
      : 0;

  return (
    <main className="min-h-screen bg-slate-950 text-white">

      {/* =====================================================
          CABEÇALHO
      ====================================================== */}

      <header className="border-b border-slate-800 bg-slate-900">

        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">

          <div>

            <button
              onClick={voltar}
              className="mb-3 text-sm text-slate-400 transition hover:text-white"
            >
              ← Voltar
            </button>

            <div className="flex flex-wrap items-center gap-3">

              <h1 className="text-2xl font-bold">
                Conferência #{conferenciaId}
              </h1>

              <span
                className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${classeStatus(
                  statusAtual
                )}`}
              >
                {statusAtual}
              </span>

            </div>

            <p className="mt-1 text-sm text-slate-500">
              Versão {dados.versao}
            </p>

          </div>

          <div className="text-right">

            <p className="text-xs uppercase tracking-wide text-slate-500">
              Perfil
            </p>

            <p className="font-semibold">
              {usuario?.perfil || "-"}
            </p>

          </div>

        </div>

      </header>


      <div className="mx-auto max-w-7xl px-6 py-8">


        {/* ===================================================
            AVISO DO AUDITOR
        ==================================================== */}

        {ehAuditor &&
          statusAtual === "FINALIZADA" && (

            <div className="mb-6 rounded-xl border border-emerald-900 bg-emerald-950/30 p-5">

              <p className="font-semibold text-emerald-300">
                Conferência aguardando auditoria
              </p>

              <p className="mt-1 text-sm text-emerald-400">
                Revise os itens, divergências e justificativas
                antes de aprovar ou reprovar.
              </p>

            </div>
        )}


        {/* ===================================================
            AVISO DE REABERTURA
        ==================================================== */}

        {statusAtual === "REABERTA" && (

          <div className="mb-6 rounded-xl border border-orange-900 bg-orange-950/20 p-5">

            <p className="font-semibold text-orange-300">
              Conferência reaberta
            </p>

            <p className="mt-1 text-sm text-orange-400">
              Esta é a versão {dados.versao}.
              As divergências desta versão precisam ser
              justificadas antes do fechamento.
            </p>

          </div>
        )}


        {/* ===================================================
            AÇÕES
        ==================================================== */}

        <div className="mb-6 rounded-xl border border-slate-800 bg-slate-900 p-5">

          <div className="flex flex-wrap items-center justify-between gap-4">

            <div>

              <p className="text-sm font-semibold">
                Ações da conferência
              </p>

              <p className="mt-1 text-xs text-slate-500">
                As ações disponíveis dependem do perfil e do status.
              </p>

            </div>

            <div className="flex flex-wrap gap-3">

              {podeFechar && (

                <button
                  onClick={fechar}
                  disabled={fechando}
                  className="rounded-xl bg-emerald-800 px-5 py-2.5 text-sm font-semibold text-emerald-50 transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {fechando
                    ? "Fechando..."
                    : "Finalizar"}
                </button>

              )}

              {podeAuditar && (

                <button
                  onClick={aprovar}
                  disabled={processandoAuditoria}
                  className="rounded-xl bg-blue-800 px-5 py-2.5 text-sm font-semibold text-blue-50 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {processandoAuditoria
                    ? "Processando..."
                    : "Aprovar"}
                </button>

              )}

              {podeAuditar && (

                <button
                  onClick={reprovar}
                  disabled={processandoAuditoria}
                  className="rounded-xl bg-red-900 px-5 py-2.5 text-sm font-semibold text-red-100 transition hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {processandoAuditoria
                    ? "Processando..."
                    : "Reprovar"}
                </button>

              )}

              {podeReabrir && (

                <button
                  onClick={() => {
                    setErroAuditoria("");
                    setAbrirReabertura(true);
                  }}
                  disabled={processandoAuditoria}
                  className="rounded-xl border border-orange-800 bg-orange-950/40 px-5 py-2.5 text-sm font-semibold text-orange-300 transition hover:bg-orange-900/50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reabrir
                </button>

              )}

            </div>

          </div>


          {erroFechamento && (

            <div className="mt-4 rounded-lg border border-red-900 bg-red-950/30 p-4 text-sm text-red-300">
              {erroFechamento}
            </div>

          )}


          {erroAuditoria && (

            <div className="mt-4 rounded-lg border border-red-900 bg-red-950/30 p-4">

              <p className="font-semibold text-red-300">
                Não foi possível processar a auditoria
              </p>

              <p className="mt-1 text-sm text-red-400">
                {erroAuditoria}
              </p>

            </div>

          )}

        </div>


        {/* ===================================================
            FORMULÁRIO DE REABERTURA
        ==================================================== */}

        {abrirReabertura && (

          <div className="mb-6 rounded-xl border border-orange-900 bg-orange-950/20 p-6">

            <h3 className="font-semibold text-orange-300">
              Reabrir conferência
            </h3>

            <p className="mt-1 text-sm text-orange-400">
              Informe obrigatoriamente o motivo da reabertura.
              Essa informação ficará registrada no histórico.
            </p>

            <textarea
              value={motivoReabertura}
              onChange={(event) =>
                setMotivoReabertura(
                  event.target.value
                )
              }
              placeholder="Ex.: Divergência encontrada durante a auditoria. Necessário realizar nova contagem."
              rows={4}
              disabled={processandoAuditoria}
              className="mt-4 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-orange-700 focus:ring-2 focus:ring-orange-900 disabled:opacity-50"
            />

            <div className="mt-4 flex justify-end gap-3">

              <button
                onClick={() => {
                  setAbrirReabertura(false);
                  setMotivoReabertura("");
                  setErroAuditoria("");
                }}
                disabled={processandoAuditoria}
                className="rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-semibold text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                onClick={reabrir}
                disabled={processandoAuditoria}
                className="rounded-xl bg-orange-800 px-5 py-2.5 text-sm font-semibold text-orange-50 transition hover:bg-orange-700 disabled:opacity-50"
              >
                {processandoAuditoria
                  ? "Reabrindo..."
                  : "Confirmar reabertura"}
              </button>

            </div>

          </div>

        )}


        {/* ===================================================
            RESUMO
        ==================================================== */}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">

          <Resumo
            titulo="Itens"
            valor={dados.total_itens}
          />

          <Resumo
            titulo="Conferidos"
            valor={conferidos}
          />

          <Resumo
            titulo="Corretos"
            valor={corretos}
          />

          <Resumo
            titulo="Divergências"
            valor={dados.divergentes}
          />

          <Resumo
            titulo="Progresso"
            valor={`${percentual}%`}
          />

        </div>


        {/* ===================================================
            PROGRESSO
        ==================================================== */}

        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">

          <div className="mb-2 flex justify-between text-sm">

            <span className="text-slate-400">
              Progresso da conferência
            </span>

            <span className="font-semibold">
              {percentual}%
            </span>

          </div>

          <div className="h-3 overflow-hidden rounded-full bg-slate-800">

            <div
              className="h-full rounded-full bg-emerald-700 transition-all"
              style={{
                width: `${percentual}%`,
              }}
            />

          </div>

        </div>


        {/* ===================================================
            TIMELINE
        ==================================================== */}

        <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900">

          <div className="border-b border-slate-800 px-6 py-4">

            <h3 className="font-semibold">
              Histórico da conferência
            </h3>

            <p className="mt-1 text-xs text-slate-500">
              Registro das alterações e decisões realizadas durante o processo.
            </p>

          </div>

          {timeline.length === 0 ? (

            <div className="px-6 py-10 text-center">

              <p className="text-sm text-slate-500">
                Nenhum evento registrado.
              </p>

            </div>

          ) : (

            <div className="divide-y divide-slate-800">

              {timeline.map(
                (evento, index) => (

                  <div
                    key={`${evento.data}-${index}`}
                    className="px-6 py-5"
                  >

                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">

                      <div>

                        <p className="font-semibold text-slate-200">
                          {evento.evento ||
                            evento.acao ||
                            "Evento"}
                        </p>

                        {evento.usuario && (

                          <p className="mt-1 text-xs text-slate-500">
                            Usuário: {evento.usuario}
                          </p>

                        )}

                        {evento.motivo && (

                          <p className="mt-2 text-sm text-slate-400">
                            {evento.motivo}
                          </p>

                        )}

                      </div>

                      <div className="text-left sm:text-right">

                        {evento.versao !== undefined && (

                          <p className="text-xs font-medium text-slate-400">
                            Versão {evento.versao}
                          </p>

                        )}

                        {evento.data && (

                          <p className="mt-1 text-xs text-slate-600">
                            {new Date(
                              evento.data
                            ).toLocaleString(
                              "pt-BR"
                            )}
                          </p>

                        )}

                      </div>

                    </div>

                  </div>

                )
              )}

            </div>

          )}

        </div>


        {/* ===================================================
            ITENS
        ==================================================== */}

        <section className="mt-8 rounded-xl border border-slate-800 bg-slate-900">

          <div className="border-b border-slate-800 px-6 py-4">

            <h2 className="font-semibold">
              Itens da conferência
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Comparação entre quantidade esperada e quantidade contada.
            </p>

          </div>


          {dados.itens.length === 0 ? (

            <div className="px-6 py-12 text-center">

              <p className="text-sm text-slate-500">
                Nenhum item encontrado.
              </p>

            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full text-sm">

                <thead>

                  <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-500">

                    <th className="px-6 py-4">
                      Código
                    </th>

                    <th className="px-6 py-4">
                      Produto
                    </th>

                    <th className="px-6 py-4 text-right">
                      XML
                    </th>

                    <th className="px-6 py-4 text-right">
                      Contado
                    </th>

                    <th className="px-6 py-4 text-right">
                      Diferença
                    </th>

                    <th className="px-6 py-4">
                      Divergência
                    </th>

                    <th className="px-6 py-4">
                      Justificativa
                    </th>

                  </tr>

                </thead>


                <tbody className="divide-y divide-slate-800">

                  {dados.itens.map(
                    (item) => {

                      const justificando =
                        justificativaAberta ===
                        item.divergencia_id;

                      return (

                        <tr
                          key={item.codigo}
                          className={
                            item.divergente
                              ? "bg-red-950/10"
                              : ""
                          }
                        >

                          <td className="px-6 py-5 font-semibold text-slate-200">
                            {item.codigo}
                          </td>

                          <td className="px-6 py-5">

                            <p className="font-medium text-slate-200">
                              {item.descricao || "-"}
                            </p>

                          </td>

                          <td className="px-6 py-5 text-right text-slate-300">
                            {item.xml}
                          </td>

                          <td className="px-6 py-5 text-right text-slate-300">
                            {item.contado}
                          </td>

                          <td
                            className={`px-6 py-5 text-right font-semibold ${
                              item.diferenca < 0
                                ? "text-red-400"
                                : item.diferenca > 0
                                ? "text-orange-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {item.diferenca > 0
                              ? `+${item.diferenca}`
                              : item.diferenca}
                          </td>

                          <td className="px-6 py-5">

                            {item.divergente ? (

                              <div>

                                <span className="font-medium text-red-300">
                                  {formatarTipo(
                                    item.tipo_divergencia
                                  )}
                                </span>

                                {item.divergencia_id && (

                                  <p className="mt-1 text-xs text-slate-600">
                                    ID #{item.divergencia_id}
                                  </p>

                                )}

                              </div>

                            ) : (

                              <span className="text-emerald-400">
                                Sem divergência
                              </span>

                            )}

                          </td>


                          <td className="min-w-[320px] px-6 py-5">

                            {!item.divergente ? (

                              <span className="text-slate-600">
                                —
                              </span>

                            ) : item.justificado ? (

                              <div className="rounded-lg border border-emerald-900 bg-emerald-950/20 p-3">

                                <div className="flex items-center justify-between gap-3">

                                  <span className="font-semibold text-emerald-400">
                                    ✓ Justificado
                                  </span>

                                  {item.justificativa_tipo && (

                                    <span className="text-xs text-slate-500">
                                      {formatarTipo(
                                        item.justificativa_tipo
                                      )}
                                    </span>

                                  )}

                                </div>

                                {item.justificativa_descricao && (

                                  <p className="mt-2 text-sm leading-5 text-slate-400">
                                    {item.justificativa_descricao}
                                  </p>

                                )}

                              </div>

                            ) : podeJustificar ? (

                              <div className="space-y-3">

                                {!justificando ? (

                                  <>

                                    <span className="text-orange-400">
                                      Pendente
                                    </span>

                                    <div>

                                      <button
                                        onClick={() =>
                                          abrirJustificativa(
                                            item
                                          )
                                        }
                                        className="rounded-lg border border-orange-800 bg-orange-950/30 px-3 py-2 text-xs font-semibold text-orange-300 transition hover:bg-orange-900/40"
                                      >
                                        Justificar
                                      </button>

                                    </div>

                                  </>

                                ) : (

                                  <div className="rounded-xl border border-orange-900 bg-orange-950/20 p-4">

                                    <p className="mb-3 text-sm font-semibold text-orange-300">
                                      Justificar divergência
                                    </p>

                                    <select
                                      value={justificativaTipo}
                                      onChange={(event) =>
                                        setJustificativaTipo(
                                          event.target.value
                                        )
                                      }
                                      disabled={
                                        processandoJustificativa
                                      }
                                      className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-orange-700 disabled:opacity-50"
                                    >

                                      <option value="">
                                        Selecione o tipo
                                      </option>

                                      {TIPOS_JUSTIFICATIVA.map(
                                        (tipo) => (

                                          <option
                                            key={tipo.valor}
                                            value={tipo.valor}
                                          >
                                            {tipo.label}
                                          </option>

                                        )
                                      )}

                                    </select>


                                    <textarea
                                      value={
                                        justificativaDescricao
                                      }
                                      onChange={(event) =>
                                        setJustificativaDescricao(
                                          event.target.value
                                        )
                                      }
                                      placeholder="Descreva o motivo da divergência..."
                                      rows={4}
                                      disabled={
                                        processandoJustificativa
                                      }
                                      className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600 focus:border-orange-700 disabled:opacity-50"
                                    />


                                    {erroJustificativa && (

                                      <div className="rounded-lg border border-red-900 bg-red-950/30 p-3 text-xs text-red-300">
                                        {erroJustificativa}
                                      </div>

                                    )}


                                    <div className="flex justify-end gap-2">

                                      <button
                                        onClick={
                                          cancelarJustificativa
                                        }
                                        disabled={
                                          processandoJustificativa
                                        }
                                        className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                                      >
                                        Cancelar
                                      </button>

                                      <button
                                        onClick={() =>
                                          justificar(
                                            item
                                          )
                                        }
                                        disabled={
                                          processandoJustificativa
                                        }
                                        className="rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-emerald-50 hover:bg-emerald-700 disabled:opacity-50"
                                      >
                                        {processandoJustificativa
                                          ? "Salvando..."
                                          : "Salvar justificativa"}
                                      </button>

                                    </div>

                                  </div>

                                )}

                              </div>

                            ) : (

                              <div>

                                <span className="text-orange-400">
                                  Pendente
                                </span>

                                {ehAuditor &&
                                  statusAtual ===
                                    "FINALIZADA" && (

                                    <p className="mt-1 text-xs text-slate-600">
                                      Aguardando justificativa do conferente.
                                    </p>

                                  )}

                              </div>

                            )}

                          </td>

                        </tr>

                      );
                    }
                  )}

                </tbody>

              </table>

            </div>

          )}

        </section>

      </div>

    </main>
  );
}


/* ============================================================
   RESUMO
============================================================ */

function Resumo({
  titulo,
  valor,
}: {
  titulo: string;
  valor: number | string;
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