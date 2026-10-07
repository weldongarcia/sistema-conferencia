"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Search, Upload } from "lucide-react";

import {
  buscarConferencia,
  buscarTimelineConferencia,
  buscarUsuarioAtual,
  fecharConferencia,
  aprovarConferencia,
  reprovarConferencia,
  reabrirConferencia,
  justificarDivergencia,
  importarXml,
  ehSessaoExpirada,
} from "../../../../services/api";
import {
  limparSessao,
  tratarSessaoExpirada,
} from "../../../../services/sessao";

import AppShell from "../../../../components/layout/AppShell";
import {
  MENU_CONFERENCIAS,
  menuPorPerfil,
} from "../../../../components/layout/menu";
import EmptyState from "../../../../components/ui/EmptyState";
import { estiloStatus } from "../../../../components/ui/StatusBadge";

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
  descricao?: string | null;
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

/*
 * Busca a timeline sem lançar erro, para que uma falha
 * no histórico não bloqueie a tela da conferência.
 */
async function carregarTimeline(
  token: string,
  conferenciaId: number,
): Promise<{
  eventos: EventoTimeline[];
  erro: string;
  sessaoExpirada?: unknown;
}> {
  try {
    const eventos = await buscarTimelineConferencia(token, conferenciaId);

    return { eventos: Array.isArray(eventos) ? eventos : [], erro: "" };
  } catch (error) {
    if (ehSessaoExpirada(error)) {
      return { eventos: [], erro: "", sessaoExpirada: error };
    }

    console.error(error);

    return {
      eventos: [],
      erro: "Não foi possível carregar o histórico da conferência.",
    };
  }
}

export default function ConferenciaDetalhePage() {
  const params = useParams();
  const router = useRouter();

  const [dados, setDados] = useState<DadosConferencia | null>(null);

  const [mostrarHistorico, setMostrarHistorico] = useState(false);

  const [usuario, setUsuario] = useState<Usuario | null>(null);

  const [timeline, setTimeline] = useState<EventoTimeline[]>([]);

  const [carregando, setCarregando] = useState(true);

  const [erro, setErro] = useState("");

  const [erroTimeline, setErroTimeline] = useState("");

  const [erroAtualizacao, setErroAtualizacao] = useState("");

  const [erroFechamento, setErroFechamento] = useState("");

  const [erroAuditoria, setErroAuditoria] = useState("");

  const [acaoAuditoria, setAcaoAuditoria] = useState<
    "aprovar" | "reprovar" | "reabrir" | null
  >(null);

  const processandoAuditoria = acaoAuditoria !== null;

  const [fechando, setFechando] = useState(false);

  const [importandoXml, setImportandoXml] = useState(false);

  const [erroImportacaoXml, setErroImportacaoXml] = useState("");

  const [abrirReabertura, setAbrirReabertura] = useState(false);

  const [motivoReabertura, setMotivoReabertura] = useState("");

  const [abrirReprovacao, setAbrirReprovacao] = useState(false);

  const [motivoReprovacao, setMotivoReprovacao] = useState("");

  const [justificativaAberta, setJustificativaAberta] = useState<number | null>(
    null,
  );

  const [justificativaTipo, setJustificativaTipo] = useState("");

  const [justificativaDescricao, setJustificativaDescricao] = useState("");

  const [processandoJustificativa, setProcessandoJustificativa] =
    useState(false);

  const [erroJustificativa, setErroJustificativa] = useState("");

  const [buscaItens, setBuscaItens] = useState("");

  const [filtroItens, setFiltroItens] = useState<
    "TODOS" | "DIVERGENCIAS" | "PENDENTES" | "SEM_DIVERGENCIA"
  >("TODOS");

  const conferenciaId = Number(params.id);

  useEffect(() => {
    async function carregar() {
      try {
        const token = localStorage.getItem("token");

        if (!token) {
          router.push("/login");
          return;
        }

        if (!conferenciaId) {
          throw new Error("ID da conferência inválido.");
        }

        const [usuarioAtual, resultado] = await Promise.all([
          buscarUsuarioAtual(token),
          buscarConferencia(token, conferenciaId),
        ]);

        setUsuario(usuarioAtual);
        setDados(resultado);

        // O histórico é secundário: uma falha nele não impede
        // a abertura da conferência.
        const historico = await carregarTimeline(token, conferenciaId);

        if (historico.sessaoExpirada) {
          tratarSessaoExpirada(historico.sessaoExpirada, router);
          return;
        }

        setTimeline(historico.eventos);
        setErroTimeline(historico.erro);
      } catch (error) {
        if (tratarSessaoExpirada(error, router)) return;

        console.error(error);

        setErro(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar a conferência.",
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

  /*
   * Recarrega a conferência após uma ação.
   *
   * Nunca lança erro: a ação já foi concluída no backend,
   * então uma falha aqui não pode ser exibida como falha
   * da ação.
   */
  async function atualizarDados() {
    const token = localStorage.getItem("token");

    if (!token) {
      router.push("/login");
      return;
    }

    setErroAtualizacao("");

    try {
      const atualizado = await buscarConferencia(token, conferenciaId);

      setDados(atualizado);
    } catch (error) {
      if (tratarSessaoExpirada(error, router)) return;

      console.error(error);

      setErroAtualizacao(
        "A operação foi concluída, mas não foi possível atualizar a tela. Recarregue a página.",
      );
    }

    const historico = await carregarTimeline(token, conferenciaId);

    if (historico.sessaoExpirada) {
      tratarSessaoExpirada(historico.sessaoExpirada, router);
      return;
    }

    setTimeline(historico.eventos);
    setErroTimeline(historico.erro);
  }

  async function fechar() {
    if (fechando) return;

    const confirmar = window.confirm(
      "Deseja realmente fechar esta conferência?\n\n" +
        "Após o fechamento, ela será encaminhada para o fluxo de auditoria.",
    );

    if (!confirmar) return;

    try {
      setFechando(true);
      setErroFechamento("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await fecharConferencia(token, conferenciaId);

      await atualizarDados();
    } catch (error) {
      if (tratarSessaoExpirada(error, router)) return;

      console.error(error);

      setErroFechamento(
        error instanceof Error
          ? error.message
          : "Não foi possível fechar a conferência.",
      );
    } finally {
      setFechando(false);
    }
  }

  async function importarArquivoXml(arquivo: File) {
    if (importandoXml) return;

    try {
      setImportandoXml(true);
      setErroImportacaoXml("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await importarXml(token, conferenciaId, arquivo);

      await atualizarDados();
    } catch (error) {
      if (tratarSessaoExpirada(error, router)) return;

      console.error(error);

      setErroImportacaoXml(
        error instanceof Error
          ? error.message
          : "Não foi possível importar o arquivo XML.",
      );
    } finally {
      setImportandoXml(false);
    }
  }

  async function aprovar() {
    if (processandoAuditoria) return;

    const confirmar = window.confirm(
      "Deseja aprovar esta conferência?\n\n" +
        "Após a aprovação, ela será considerada aprovada pela auditoria.",
    );

    if (!confirmar) return;

    try {
      setAcaoAuditoria("aprovar");
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await aprovarConferencia(token, conferenciaId);

      await atualizarDados();
    } catch (error) {
      if (tratarSessaoExpirada(error, router)) return;

      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível aprovar a conferência.",
      );
    } finally {
      setAcaoAuditoria(null);
    }
  }

  async function reprovar() {
    if (processandoAuditoria) return;

    const motivo = motivoReprovacao.trim();

    if (!motivo) {
      setErroAuditoria("Informe o motivo da reprovação.");
      return;
    }

    try {
      setAcaoAuditoria("reprovar");
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await reprovarConferencia(token, conferenciaId, motivo);

      setMotivoReprovacao("");
      setAbrirReprovacao(false);

      await atualizarDados();
    } catch (error) {
      if (tratarSessaoExpirada(error, router)) return;

      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível reprovar a conferência.",
      );
    } finally {
      setAcaoAuditoria(null);
    }
  }

  async function reabrir() {
    if (processandoAuditoria) return;

    const motivo = motivoReabertura.trim();

    if (!motivo) {
      setErroAuditoria("Informe o motivo da reabertura.");
      return;
    }

    try {
      setAcaoAuditoria("reabrir");
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await reabrirConferencia(token, conferenciaId, motivo);

      setMotivoReabertura("");
      setAbrirReabertura(false);

      await atualizarDados();
    } catch (error) {
      if (tratarSessaoExpirada(error, router)) return;

      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível reabrir a conferência.",
      );
    } finally {
      setAcaoAuditoria(null);
    }
  }

  function abrirJustificativa(item: ItemConferencia) {
    setJustificativaAberta(item.divergencia_id);

    setJustificativaTipo(item.justificativa_tipo || "");

    setJustificativaDescricao(item.justificativa_descricao || "");

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
      setErroJustificativa("Divergência inválida.");
      return;
    }

    if (!justificativaTipo) {
      setErroJustificativa("Selecione o tipo da justificativa.");
      return;
    }

    if (!justificativaDescricao.trim()) {
      setErroJustificativa("Informe a descrição da justificativa.");
      return;
    }

    try {
      setProcessandoJustificativa(true);
      setErroJustificativa("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await justificarDivergencia(
        token,
        item.divergencia_id,
        justificativaTipo,
        justificativaDescricao.trim(),
      );

      cancelarJustificativa();

      await atualizarDados();
    } catch (error) {
      if (tratarSessaoExpirada(error, router)) return;

      console.error(error);

      setErroJustificativa(
        error instanceof Error
          ? error.message
          : "Não foi possível justificar a divergência.",
      );
    } finally {
      setProcessandoJustificativa(false);
    }
  }

  function formatarTipo(tipo: string | null) {
    if (!tipo) return "-";

    return tipo
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(/\b\w/g, (letra) => letra.toUpperCase());
  }

  function classeStatus(status: string) {
    return `border ${estiloStatus(status).classes}`;
  }

  if (carregando) {
    return (
      <main className="min-h-screen bg-canvas text-ink">
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted">Carregando conferência...</p>
        </div>
      </main>
    );
  }

  if (erro || !dados) {
    return (
      <main className="min-h-screen bg-canvas text-ink">
        <div className="mx-auto max-w-3xl px-6 py-12">
          <div className="rounded-2xl border border-danger/30 bg-white p-6 shadow-card">
            <h1 className="text-lg font-semibold text-danger">
              Não foi possível carregar a conferência
            </h1>

            <p className="mt-2 text-sm text-danger">
              {erro || "Nenhum dado encontrado."}
            </p>

            <button
              onClick={voltar}
              className="mt-5 rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-light"
            >
              Voltar
            </button>
          </div>
        </div>
      </main>
    );
  }

  const statusAtual = dados.status_conferencia.toUpperCase();

  const ehAuditor = usuario?.perfil === "AUDITOR";

  const ehConferente = usuario?.perfil === "CONFERENTE";

  const podeJustificar =
    ehConferente && (statusAtual === "RASCUNHO" || statusAtual === "REABERTA");

  const podeFechar =
    ehConferente && (statusAtual === "RASCUNHO" || statusAtual === "REABERTA");

  const podeImportarXml = podeFechar;

  const divergenciasPendentes = dados.itens.filter(
    (item) => item.divergente && !item.justificado,
  ).length;

  const podeAuditar =
    ehAuditor && statusAtual === "FINALIZADA";

  const podeReabrir =
    ehAuditor && (statusAtual === "FINALIZADA" || statusAtual === "REPROVADA");

  // A timeline vem ordenada da mais recente para a mais antiga.
  const motivoReprovacaoAtual =
    statusAtual === "REPROVADA"
      ? timeline.find(
          (evento) =>
            evento.evento === "Conferência reprovada" &&
            evento.versao === dados.versao,
        )?.motivo ?? null
      : null;
  const conferidos = dados.itens.filter((item) => item.contado > 0).length;

  const corretos = dados.itens.filter(
    (item) => item.contado > 0 && !item.divergente,
  ).length;

  const percentual =
    dados.total_itens > 0
      ? Math.round((conferidos / dados.total_itens) * 100)
      : 0;

  const buscaNormalizada = buscaItens.trim().toLowerCase();

  const itensFiltrados = dados.itens.filter((item) => {
    /* ======================================================
       BUSCA
    ====================================================== */

    const correspondeBusca =
      !buscaNormalizada ||
      item.codigo.toLowerCase().includes(buscaNormalizada) ||
      (item.descricao || "").toLowerCase().includes(buscaNormalizada);

    if (!correspondeBusca) {
      return false;
    }

    /* ======================================================
       FILTRO
    ====================================================== */

    if (filtroItens === "DIVERGENCIAS") {
      return item.divergente;
    }

    if (filtroItens === "PENDENTES") {
      return item.divergente && !item.justificado;
    }

    if (filtroItens === "SEM_DIVERGENCIA") {
      return !item.divergente;
    }

    return true;
  });

  return (
    <AppShell
      usuario={usuario?.username}
      perfil={usuario?.perfil}
      menuItems={menuPorPerfil(usuario?.perfil)}
      activeKey={MENU_CONFERENCIAS}
      onLogout={() => {
        limparSessao();

        router.push("/login");
      }}
    >
      <div className="mx-auto w-full max-w-[1500px] px-5 py-6 sm:px-8">
        {/* =====================================================
            CABEÇALHO DA CONFERÊNCIA
        ====================================================== */}

        <section className="mb-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <button
                onClick={voltar}
                className="mb-3 inline-flex items-center gap-2 text-xs font-medium text-muted transition hover:text-brand"
              >
                <span>←</span>
                Voltar para conferências
              </button>

              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-brand sm:text-3xl">
                  Conferência #{conferenciaId}
                </h1>

                <span
                  className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold ${classeStatus(
                    statusAtual,
                  )}`}
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  {statusAtual}
                </span>
              </div>

              <p className="mt-2 text-sm text-muted">
                Versão {dados.versao} • {dados.total_itens} itens
              </p>
            </div>

            <div className="rounded-2xl border border-line bg-white px-4 py-3 shadow-card">
              <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">
                Perfil atual
              </p>

              <p className="mt-1 text-sm font-semibold text-brand">
                {usuario?.perfil || "-"}
              </p>
            </div>
          </div>
        </section>

        {/* ===================================================
    AVISO DO AUDITOR
==================================================== */}

        {ehAuditor && statusAtual === "FINALIZADA" && (
          <div className="mb-6 rounded-2xl border border-info/30 bg-info-soft p-5">
            <p className="font-semibold text-info">
              Conferência aguardando auditoria
            </p>

            <p className="mt-1 text-sm text-info">
              Revise os itens, divergências e justificativas antes de aprovar ou
              reprovar.
            </p>
          </div>
        )}

        {ehAuditor &&
          statusAtual === "FINALIZADA" &&
          divergenciasPendentes > 0 && (
            <div className="mb-6 rounded-2xl border border-warning/30 bg-warning-soft p-5">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-warning/15 text-xs font-bold text-warning-strong">
                  !
                </div>

                <div>
                  <p className="font-semibold text-warning-strong">
                    Auditoria aguardando justificativas
                  </p>

                  <p className="mt-1 text-sm leading-6 text-warning-strong">
                    Existem{" "}
                    <strong className="font-semibold text-warning-strong">
                      {divergenciasPendentes}
                    </strong>{" "}
                    divergência(s) sem justificativa. A aprovação ficará
                    disponível somente após todas as divergências serem
                    justificadas.
                  </p>
                </div>
              </div>
            </div>
          )}

        {/* ===================================================
            AVISO DE REABERTURA
        ==================================================== */}

        {statusAtual === "REABERTA" && (
          <div className="mb-6 rounded-2xl border border-attention/30 bg-attention-soft p-5">
            <p className="font-semibold text-attention-strong">Conferência reaberta</p>

            <p className="mt-1 text-sm text-attention-strong">
              Esta é a versão {dados.versao}. As divergências desta versão
              precisam ser justificadas antes do fechamento.
            </p>
          </div>
        )}

        {/* ===================================================
            AVISO DE REPROVAÇÃO
        ==================================================== */}

        {statusAtual === "REPROVADA" && (
          <div className="mb-6 rounded-2xl border border-danger/30 bg-danger-soft p-5">
            <p className="font-semibold text-danger">Conferência reprovada</p>

            {motivoReprovacaoAtual && (
              <p className="mt-1 text-sm text-danger">
                <strong className="font-semibold">Motivo:</strong>{" "}
                {motivoReprovacaoAtual}
              </p>
            )}

            <p className="mt-1 text-sm text-danger">
              {ehAuditor
                ? "Reabra a conferência para permitir uma nova contagem."
                : "Aguarde a reabertura pelo auditor para realizar uma nova contagem."}
            </p>
          </div>
        )}

        {/* ===================================================
            AÇÕES
        ==================================================== */}

        <div className="mb-6 rounded-2xl border border-line bg-white p-5 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-brand">
                Ações da conferência
              </p>

              <p className="mt-1 text-xs text-muted">
                As ações disponíveis dependem do perfil e do status.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              {podeImportarXml && (
                <label
                  className={[
                    "inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-line bg-white px-5 py-2.5 text-sm font-semibold text-brand transition hover:border-brand-light hover:bg-canvas",
                    importandoXml ? "pointer-events-none opacity-50" : "",
                  ].join(" ")}
                >
                  <input
                    type="file"
                    accept=".xml,application/xml,text/xml"
                    className="sr-only"
                    disabled={importandoXml}
                    onChange={(event) => {
                      const arquivo = event.target.files?.[0];

                      if (arquivo) {
                        void importarArquivoXml(arquivo);
                      }

                      event.target.value = "";
                    }}
                  />

                  <Upload size={17} strokeWidth={1.8} aria-hidden="true" />
                  {importandoXml ? "Importando..." : "Importar XML"}
                </label>
              )}

              {podeFechar && (
                <button
                  onClick={fechar}
                  disabled={fechando}
                  className="rounded-xl bg-success px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-success-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {fechando ? "Fechando..." : "Finalizar"}
                </button>
              )}

              {ehAuditor && statusAtual === "FINALIZADA" && (
                <button
                  onClick={aprovar}
                  disabled={processandoAuditoria || divergenciasPendentes > 0}
                  title={
                    divergenciasPendentes > 0
                      ? `Existem ${divergenciasPendentes} divergência(s) sem justificativa.`
                      : "Aprovar conferência"
                  }
                  className={[
                    "rounded-xl px-5 py-2.5 text-sm font-semibold transition",
                    divergenciasPendentes > 0
                      ? "cursor-not-allowed border border-line bg-canvas text-muted"
                      : "bg-info text-white hover:bg-info-hover",
                    "disabled:cursor-not-allowed disabled:opacity-60",
                  ].join(" ")}
                >
                  {acaoAuditoria === "aprovar"
                    ? "Aprovando..."
                    : divergenciasPendentes > 0
                      ? `Aprovar (${divergenciasPendentes} pendente${divergenciasPendentes > 1 ? "s" : ""})`
                      : "Aprovar"}
                </button>
              )}

              {podeAuditar && (
                <button
                  onClick={() => {
                    setErroAuditoria("");
                    setAbrirReabertura(false);
                    setAbrirReprovacao(true);
                  }}
                  disabled={processandoAuditoria}
                  className="rounded-xl bg-danger px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-danger-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reprovar
                </button>
              )}

              {podeReabrir && (
                <button
                  onClick={() => {
                    setErroAuditoria("");
                    setAbrirReprovacao(false);
                    setAbrirReabertura(true);
                  }}
                  disabled={processandoAuditoria}
                  className="rounded-xl border border-attention/40 bg-attention-soft px-5 py-2.5 text-sm font-semibold text-attention-strong transition hover:bg-attention-soft-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reabrir
                </button>
              )}
            </div>
          </div>

          {erroAtualizacao && (
            <div className="mt-4 rounded-xl border border-warning/30 bg-warning-soft p-4 text-sm text-warning-strong">
              {erroAtualizacao}
            </div>
          )}

          {erroFechamento && (
            <div className="mt-4 rounded-xl border border-danger/30 bg-danger-soft p-4 text-sm text-danger">
              {erroFechamento}
            </div>
          )}

          {erroImportacaoXml && (
            <div className="mt-4 rounded-xl border border-danger/30 bg-danger-soft p-4 text-sm text-danger">
              {erroImportacaoXml}
            </div>
          )}

          {erroAuditoria && (
            <div className="mt-4 rounded-xl border border-danger/30 bg-danger-soft p-4">
              <p className="font-semibold text-danger">
                Não foi possível processar a auditoria
              </p>

              <p className="mt-1 text-sm text-danger">{erroAuditoria}</p>
            </div>
          )}
        </div>

        {/* ===================================================
            FORMULÁRIO DE REABERTURA
        ==================================================== */}

        {abrirReabertura && (
          <div className="mb-6 rounded-2xl border border-attention/30 bg-white p-6 shadow-card">
            <h3 className="font-semibold text-attention-strong">
              Reabrir conferência
            </h3>

            <p className="mt-1 text-sm text-attention-strong">
              Informe obrigatoriamente o motivo da reabertura. Essa informação
              ficará registrada no histórico.
            </p>

            <textarea
              value={motivoReabertura}
              onChange={(event) => setMotivoReabertura(event.target.value)}
              placeholder="Ex.: Divergência encontrada durante a auditoria. Necessário realizar nova contagem."
              rows={4}
              disabled={processandoAuditoria}
              className="mt-4 w-full rounded-xl border border-line bg-canvas px-4 py-3 text-sm text-ink outline-none transition placeholder:text-muted focus:border-attention focus:ring-2 focus:ring-attention/15 disabled:opacity-50"
            />

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setAbrirReabertura(false);
                  setMotivoReabertura("");
                  setErroAuditoria("");
                }}
                disabled={processandoAuditoria}
                className="rounded-xl border border-line px-5 py-2.5 text-sm font-semibold text-brand transition hover:bg-canvas disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                onClick={reabrir}
                disabled={processandoAuditoria}
                className="rounded-xl bg-attention px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-attention-strong disabled:opacity-50"
              >
                {acaoAuditoria === "reabrir"
                  ? "Reabrindo..."
                  : "Confirmar reabertura"}
              </button>
            </div>
          </div>
        )}

        {/* ===================================================
            FORMULÁRIO DE REPROVAÇÃO
        ==================================================== */}

        {abrirReprovacao && podeAuditar && (
          <div className="mb-6 rounded-2xl border border-danger/30 bg-white p-6 shadow-card">
            <h3 className="font-semibold text-danger">Reprovar conferência</h3>

            <p className="mt-1 text-sm text-danger">
              Informe obrigatoriamente o motivo da reprovação. Essa informação
              ficará registrada no histórico.
            </p>

            <textarea
              value={motivoReprovacao}
              onChange={(event) => setMotivoReprovacao(event.target.value)}
              placeholder="Ex.: Contagem inconsistente com a nota. Necessário recontar os itens divergentes."
              rows={4}
              disabled={processandoAuditoria}
              className="mt-4 w-full rounded-xl border border-line bg-canvas px-4 py-3 text-sm text-ink outline-none transition placeholder:text-muted focus:border-danger focus:ring-2 focus:ring-danger/15 disabled:opacity-50"
            />

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setAbrirReprovacao(false);
                  setMotivoReprovacao("");
                  setErroAuditoria("");
                }}
                disabled={processandoAuditoria}
                className="rounded-xl border border-line px-5 py-2.5 text-sm font-semibold text-brand transition hover:bg-canvas disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                onClick={reprovar}
                disabled={processandoAuditoria}
                className="rounded-xl bg-danger px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-danger-hover disabled:opacity-50"
              >
                {acaoAuditoria === "reprovar"
                  ? "Reprovando..."
                  : "Confirmar reprovação"}
              </button>
            </div>
          </div>
        )}

        {/* ===================================================
            RESUMO
        ==================================================== */}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
          <Resumo titulo="Itens" valor={dados.total_itens} />

          <Resumo titulo="Conferidos" valor={conferidos} />

          <Resumo titulo="Sem divergência" valor={corretos} />

          <Resumo titulo="Divergências" valor={dados.divergentes} />

          <Resumo
            titulo="Justificativas pendentes"
            valor={divergenciasPendentes}
          />

          <Resumo titulo="Progresso" valor={`${percentual}%`} />
        </div>

        {/* ===================================================
            PROGRESSO
        ==================================================== */}

        <div className="mt-6 rounded-2xl border border-line bg-white p-5 shadow-card">
          <div className="mb-2 flex justify-between text-sm">
            <span className="text-sm font-medium text-muted">
              Progresso da conferência
            </span>

            <span className="font-semibold text-brand">{percentual}%</span>
          </div>

          <div className="h-2.5 overflow-hidden rounded-full bg-track">
            <div
              className="h-full rounded-full bg-success transition-all"
              style={{
                width: `${percentual}%`,
              }}
            />
          </div>
        </div>

        {/* ===================================================
            ITENS
        ==================================================== */}

        <section className="mt-8 overflow-hidden rounded-2xl border border-line bg-white shadow-card">
          {/* =====================================================
      CABEÇALHO
  ====================================================== */}

          <div className="border-b border-line px-6 py-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-brand">
                  Itens da conferência
                </h2>

                <p className="mt-1 text-xs text-muted">
                  Compare a quantidade esperada com a quantidade contada.
                </p>
              </div>

              <div className="text-xs text-muted">
                Exibindo{" "}
                <span className="font-semibold text-brand">
                  {itensFiltrados.length}
                </span>{" "}
                de{" "}
                <span className="font-semibold text-brand">
                  {dados.itens.length}
                </span>{" "}
                itens
              </div>
            </div>

            {/* ===================================================
        CONTROLES
    ==================================================== */}

            <div className="mt-5 flex flex-col gap-3 lg:flex-row">
              {/* BUSCA */}

              <div className="relative flex-1">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted">
                  <Search size={17} strokeWidth={1.8} />
                </span>

                <input
                  type="text"
                  value={buscaItens}
                  onChange={(event) => setBuscaItens(event.target.value)}
                  placeholder="Buscar por código ou produto..."
                  className="h-11 w-full rounded-xl border border-line bg-canvas pl-10 pr-4 text-sm text-ink outline-none transition placeholder:text-muted focus:border-brand-light focus:bg-white focus:ring-2 focus:ring-brand-light/10"
                />
              </div>

              {/* FILTRO */}

              <select
                value={filtroItens}
                onChange={(event) =>
                  setFiltroItens(
                    event.target.value as
                      | "TODOS"
                      | "DIVERGENCIAS"
                      | "PENDENTES"
                      | "SEM_DIVERGENCIA",
                  )
                }
                className="h-11 rounded-xl border border-line bg-canvas px-4 text-sm text-ink outline-none transition focus:border-brand-light focus:bg-white focus:ring-2 focus:ring-brand-light/10"
              >
                <option value="TODOS">Todos os itens</option>

                <option value="DIVERGENCIAS">Somente divergências</option>

                <option value="PENDENTES">Justificativas pendentes</option>

                <option value="SEM_DIVERGENCIA">Sem divergência</option>
              </select>
            </div>

            {/* ===================================================
        FILTROS RÁPIDOS
    ==================================================== */}

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setFiltroItens("TODOS")}
                className={[
                  "rounded-lg border px-3 py-1.5 text-xs font-semibold transition",
                  filtroItens === "TODOS"
                    ? "border-brand-light/30 bg-success-soft text-brand-light"
                    : "border-line bg-canvas text-muted hover:bg-white hover:text-brand",
                ].join(" ")}
              >
                Todos {dados.itens.length}
              </button>

              <button
                type="button"
                onClick={() => setFiltroItens("DIVERGENCIAS")}
                className={[
                  "rounded-lg border px-3 py-1.5 text-xs font-semibold transition",
                  filtroItens === "DIVERGENCIAS"
                    ? "border-danger/30 bg-danger-soft text-danger"
                    : "border-line bg-canvas text-muted hover:bg-white hover:text-brand",
                ].join(" ")}
              >
                Divergências {dados.divergentes}
              </button>

              <button
                type="button"
                onClick={() => setFiltroItens("PENDENTES")}
                className={[
                  "rounded-lg border px-3 py-1.5 text-xs font-semibold transition",
                  filtroItens === "PENDENTES"
                    ? "border-warning/30 bg-warning-soft text-warning-strong"
                    : "border-line bg-canvas text-muted hover:bg-white hover:text-brand",
                ].join(" ")}
              >
                Pendentes{" "}
                {
                  dados.itens.filter(
                    (item) => item.divergente && !item.justificado,
                  ).length
                }
              </button>

              <button
                type="button"
                onClick={() => setFiltroItens("SEM_DIVERGENCIA")}
                className={[
                  "rounded-lg border px-3 py-1.5 text-xs font-semibold transition",
                  filtroItens === "SEM_DIVERGENCIA"
                    ? "border-success/30 bg-success-soft text-success-strong"
                    : "border-line bg-canvas text-muted hover:bg-white hover:text-brand",
                ].join(" ")}
              >
                Sem divergência{" "}
                {dados.itens.filter((item) => !item.divergente).length}
              </button>
            </div>
          </div>

          {dados.itens.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-muted">Nenhum item encontrado.</p>
            </div>
          ) : (
            <div className="max-h-[650px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-canvas">
                  <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                    <th className="px-6 py-4">Código</th>

                    <th className="px-6 py-4">Produto</th>

                    <th className="px-6 py-4 text-right">Esperado</th>

                    <th className="px-6 py-4 text-right">Contado</th>

                    <th className="px-6 py-4 text-right">Diferença</th>

                    <th className="px-6 py-4">Divergência</th>

                    <th className="px-6 py-4">Justificativa</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-line">
                  {itensFiltrados.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center">
                        <EmptyState
                          icone={<Search size={17} strokeWidth={1.8} />}
                          titulo="Nenhum item encontrado"
                          descricao="Tente alterar a busca ou o filtro selecionado."
                          acao={
                            <button
                              type="button"
                              onClick={() => {
                                setBuscaItens("");
                                setFiltroItens("TODOS");
                              }}
                              className="mt-4 rounded-lg border border-line px-4 py-2 text-xs font-semibold text-brand transition hover:border-brand-light hover:bg-canvas"
                            >
                              Limpar filtros
                            </button>
                          }
                        />
                      </td>
                    </tr>
                  ) : (
                    itensFiltrados.map((item) => {
                      const justificando =
                        justificativaAberta === item.divergencia_id;

                      return (
                        <tr
                          key={item.codigo}
                          className="transition hover:bg-canvas"
                        >
                          <td className="px-6 py-5 font-semibold text-ink">
                            {item.codigo}
                          </td>

                          <td className="px-6 py-5">
                            <p className="font-medium text-ink">
                              {item.descricao || "-"}
                            </p>
                          </td>
                          <td className="px-6 py-5 text-right">
                            <span
                              className={[
                                "inline-flex min-w-[52px] items-center justify-center rounded-lg px-2.5 py-1.5 font-bold",
                                item.diferenca < 0
                                  ? "bg-danger-soft text-danger"
                                  : item.diferenca > 0
                                    ? "bg-attention-soft text-attention-strong"
                                    : "bg-success-soft text-success-strong",
                              ].join(" ")}
                            >
                              {item.xml}
                            </span>
                          </td>

                          <td className="px-6 py-5 text-right">
                            <span
                              className={
                                item.divergente
                                  ? "font-bold text-danger"
                                  : "font-semibold text-success-strong"
                              }
                            >
                              {item.contado}
                            </span>
                          </td>

                          <td
                            className={`px-6 py-5 text-right font-semibold ${
                              item.diferenca < 0
                                ? "text-danger"
                                : item.diferenca > 0
                                  ? "text-attention-strong"
                                  : "text-success-strong"
                            }`}
                          >
                            {item.diferenca > 0
                              ? `+${item.diferenca}`
                              : item.diferenca}
                          </td>

                          <td className="px-6 py-5">
                            {item.divergente ? (
                              <div className="space-y-1.5">
                                <span className="inline-flex items-center rounded-lg border border-danger/30 bg-danger-soft px-2.5 py-1 text-xs font-semibold text-danger">
                                  Divergência
                                </span>

                                <p className="text-xs font-medium text-danger">
                                  {formatarTipo(item.tipo_divergencia)}
                                </p>

                                {item.divergencia_id && (
                                  <p className="text-xs text-muted">
                                    ID #{item.divergencia_id}
                                  </p>
                                )}
                              </div>
                            ) : (
                              <span className="inline-flex items-center rounded-lg border border-success/30 bg-success-soft px-2.5 py-1 text-xs font-semibold text-success-strong">
                                ✓ Sem divergência
                              </span>
                            )}
                          </td>

                          <td className="min-w-[320px] px-6 py-5">
                            {!item.divergente ? (
                              <span className="text-muted">—</span>
                            ) : item.justificado ? (
                              <div className="rounded-lg border border-success/30 bg-success-soft p-3">
                                <div className="flex items-center justify-between gap-3">
                                  <span className="font-semibold text-success-strong">
                                    ✓ Justificado
                                  </span>

                                  {item.justificativa_tipo && (
                                    <span className="text-xs text-muted">
                                      {formatarTipo(item.justificativa_tipo)}
                                    </span>
                                  )}
                                </div>

                                {item.justificativa_descricao && (
                                  <p className="mt-2 text-sm leading-5 text-muted">
                                    {item.justificativa_descricao}
                                  </p>
                                )}
                              </div>
                            ) : podeJustificar ? (
                              <div className="space-y-3">
                                {!justificando ? (
                                  <>
                                    <span className="text-warning-strong">
                                      Pendente
                                    </span>

                                    <div>
                                      <button
                                        onClick={() => abrirJustificativa(item)}
                                        className="rounded-lg border border-warning/35 bg-warning-soft px-3 py-2 text-xs font-semibold text-warning-strong transition hover:bg-warning-soft-hover"
                                      >
                                        Justificar
                                      </button>
                                    </div>
                                  </>
                                ) : (
                                  <div className="rounded-xl border border-warning/30 bg-warning-soft p-4">
                                    <p className="mb-3 text-sm font-semibold text-warning-strong">
                                      Justificar divergência
                                    </p>

                                    <select
                                      value={justificativaTipo}
                                      onChange={(event) =>
                                        setJustificativaTipo(event.target.value)
                                      }
                                      disabled={processandoJustificativa}
                                      className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-warning disabled:opacity-50"
                                    >
                                      <option value="">Selecione o tipo</option>

                                      {TIPOS_JUSTIFICATIVA.map((tipo) => (
                                        <option
                                          key={tipo.valor}
                                          value={tipo.valor}
                                        >
                                          {tipo.label}
                                        </option>
                                      ))}
                                    </select>

                                    <textarea
                                      value={justificativaDescricao}
                                      onChange={(event) =>
                                        setJustificativaDescricao(
                                          event.target.value,
                                        )
                                      }
                                      placeholder="Descreva o motivo da divergência..."
                                      rows={4}
                                      disabled={processandoJustificativa}
                                      className="mt-3 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none placeholder:text-muted focus:border-warning disabled:opacity-50"
                                    />

                                    {erroJustificativa && (
                                      <div className="rounded-lg border border-danger/30 bg-danger-soft p-3 text-xs text-danger">
                                        {erroJustificativa}
                                      </div>
                                    )}

                                    <div className="flex justify-end gap-2">
                                      <button
                                        onClick={cancelarJustificativa}
                                        disabled={processandoJustificativa}
                                        className="rounded-lg border border-line px-3 py-2 text-xs font-semibold text-brand hover:bg-white disabled:opacity-50"
                                      >
                                        Cancelar
                                      </button>

                                      <button
                                        onClick={() => justificar(item)}
                                        disabled={processandoJustificativa}
                                        className="rounded-lg bg-success px-3 py-2 text-xs font-semibold text-white hover:bg-success-hover disabled:opacity-50"
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
                                <span className="text-warning-strong">Pendente</span>

                                {ehAuditor && statusAtual === "FINALIZADA" && (
                                  <p className="mt-1 text-xs text-muted">
                                    Aguardando justificativa do conferente.
                                  </p>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* ===================================================
            HISTÓRICO DA CONFERÊNCIA
        ==================================================== */}

        <div className="mt-8">
          <button
            type="button"
            onClick={() => setMostrarHistorico((atual) => !atual)}
            className="flex w-full items-center justify-between rounded-2xl border border-line bg-white px-5 py-4 text-left shadow-card transition hover:border-brand-light/40 hover:shadow-sm"
          >
            <div>
              <p className="font-semibold text-brand">
                Histórico da conferência
              </p>

              <p className="mt-1 text-xs text-muted">
                Consulte as alterações e decisões realizadas durante o processo.
              </p>
            </div>

            <span className="ml-4 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand text-lg font-medium text-white">
              {mostrarHistorico ? "−" : "+"}
            </span>
          </button>

          {mostrarHistorico && (
            <div className="mt-3 overflow-hidden rounded-2xl border border-line bg-white shadow-card">
              {erroTimeline ? (
                <div className="px-6 py-10 text-center">
                  <p className="text-sm text-danger">{erroTimeline}</p>
                </div>
              ) : timeline.length === 0 ? (
                <div className="px-6 py-10 text-center">
                  <p className="text-sm text-muted">
                    Nenhum evento registrado.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-line">
                  {timeline.map((evento, index) => (
                    <div key={`${evento.data}-${index}`} className="px-6 py-5">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="font-semibold text-brand">
                            {evento.evento || evento.acao || "Evento"}
                          </p>

                          {evento.usuario && (
                            <p className="mt-1 text-xs text-muted">
                              Usuário: {evento.usuario}
                            </p>
                          )}

                          {evento.motivo && (
                            <p className="mt-2 text-sm text-muted">
                              {evento.motivo}
                            </p>
                          )}

                          {evento.descricao && (
                            <p className="mt-2 text-sm text-muted">
                              {evento.descricao}
                            </p>
                          )}
                        </div>

                        {evento.data && (
                          <p className="shrink-0 text-xs text-muted">
                            {new Date(evento.data).toLocaleString("pt-BR")}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

/* ============================================================
   RESUMO
============================================================ */

function Resumo({ titulo, valor }: { titulo: string; valor: number | string }) {
  const destaque =
    titulo === "Divergências" && Number(valor) > 0
      ? {
          borda: "border-danger/30",
          numero: "text-danger",
          ponto: "bg-danger",
        }
      : titulo === "Justificativas pendentes" && Number(valor) > 0
        ? {
            borda: "border-warning/30",
            numero: "text-warning-strong",
            ponto: "bg-warning",
          }
        : titulo === "Sem divergência" && Number(valor) > 0
          ? {
              borda: "border-success/30",
              numero: "text-success-strong",
              ponto: "bg-success",
            }
          : titulo === "Progresso"
            ? {
                borda: "border-success/30",
                numero: "text-success-strong",
                ponto: "bg-success",
              }
            : {
                borda: "border-line",
                numero: "text-ink",
                ponto: "bg-muted",
              };

  return (
    <div
      className={[
        "rounded-2xl border bg-white p-5 shadow-card",
        "transition duration-200 hover:-translate-y-0.5 hover:shadow-md",
        destaque.borda,
      ].join(" ")}
    >
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
          {titulo}
        </p>

        <span className={`h-2 w-2 rounded-full ${destaque.ponto}`} />
      </div>

      <p
        className={`mt-3 text-3xl font-bold tracking-tight ${destaque.numero}`}
      >
        {valor}
      </p>
    </div>
  );
}
