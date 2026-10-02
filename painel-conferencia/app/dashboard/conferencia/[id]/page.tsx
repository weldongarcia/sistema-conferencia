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
  importarXml,
} from "../../../../services/api";

import AppShell from "../../../../components/layout/AppShell";

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

export default function ConferenciaDetalhePage() {
  const params = useParams();
  const router = useRouter();

  const [dados, setDados] = useState<DadosConferencia | null>(null);

  const [mostrarHistorico, setMostrarHistorico] = useState(false);

  const [usuario, setUsuario] = useState<Usuario | null>(null);

  const [timeline, setTimeline] = useState<EventoTimeline[]>([]);

  const [carregando, setCarregando] = useState(true);

  const [erro, setErro] = useState("");

  const [erroFechamento, setErroFechamento] = useState("");

  const [erroAuditoria, setErroAuditoria] = useState("");

  const [processandoAuditoria, setProcessandoAuditoria] = useState(false);

  const [fechando, setFechando] = useState(false);

  const [importandoXml, setImportandoXml] = useState(false);

  const [erroImportacaoXml, setErroImportacaoXml] = useState("");

  const [abrirReabertura, setAbrirReabertura] = useState(false);

  const [motivoReabertura, setMotivoReabertura] = useState("");

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

        const [usuarioAtual, resultado, timelineAtualizada] = await Promise.all(
          [
            buscarUsuarioAtual(token),
            buscarConferencia(token, conferenciaId),
            buscarTimelineConferencia(token, conferenciaId),
          ],
        );

        setUsuario(usuarioAtual);
        setDados(resultado);
        setTimeline(
          Array.isArray(timelineAtualizada) ? timelineAtualizada : [],
        );
      } catch (error) {
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

  async function atualizarDados() {
    const token = localStorage.getItem("token");

    if (!token) {
      router.push("/login");
      return;
    }

    const [atualizado, timelineAtualizada] = await Promise.all([
      buscarConferencia(token, conferenciaId),
      buscarTimelineConferencia(token, conferenciaId),
    ]);

    setDados(atualizado);

    setTimeline(Array.isArray(timelineAtualizada) ? timelineAtualizada : []);
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
      setProcessandoAuditoria(true);
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await aprovarConferencia(token, conferenciaId);

      await atualizarDados();
    } catch (error) {
      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível aprovar a conferência.",
      );
    } finally {
      setProcessandoAuditoria(false);
    }
  }

  async function reprovar() {
    if (processandoAuditoria) return;

    const confirmar = window.confirm(
      "Deseja reprovar esta conferência?\n\n" +
        "A conferência será marcada como REPROVADA.",
    );

    if (!confirmar) return;

    try {
      setProcessandoAuditoria(true);
      setErroAuditoria("");

      const token = localStorage.getItem("token");

      if (!token) {
        router.push("/login");
        return;
      }

      await reprovarConferencia(token, conferenciaId);

      await atualizarDados();
    } catch (error) {
      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível reprovar a conferência.",
      );
    } finally {
      setProcessandoAuditoria(false);
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
      setProcessandoAuditoria(true);
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
      console.error(error);

      setErroAuditoria(
        error instanceof Error
          ? error.message
          : "Não foi possível reabrir a conferência.",
      );
    } finally {
      setProcessandoAuditoria(false);
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
    const normalizado = status.toUpperCase();

    if (normalizado === "APROVADA") {
      return "border border-[#1DB954]/30 bg-[#EFFAF3] text-[#168C40]";
    }

    if (normalizado === "FINALIZADA") {
      return "border border-[#3578B8]/30 bg-[#EEF5FB] text-[#3578B8]";
    }

    if (normalizado === "REABERTA") {
      return "border border-[#E87524]/30 bg-[#FFF3EA] text-[#C95F16]";
    }

    if (normalizado === "RASCUNHO") {
      return "border border-[#D99000]/30 bg-[#FFF8E8] text-[#A86F00]";
    }

    if (normalizado === "REPROVADA") {
      return "border border-[#D64545]/30 bg-[#FFF5F5] text-[#D64545]";
    }

    return "border border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B]";
  }

  if (carregando) {
    return (
      <main className="min-h-screen bg-[#F6F7F5] text-[#17231D]">
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-[#64736B]">Carregando conferência...</p>
        </div>
      </main>
    );
  }

  if (erro || !dados) {
    return (
      <main className="min-h-screen bg-[#F6F7F5] text-[#17231D]">
        <div className="mx-auto max-w-3xl px-6 py-12">
          <div className="rounded-2xl border border-[#D64545]/30 bg-white p-6 shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
            <h1 className="text-lg font-semibold text-[#D64545]">
              Não foi possível carregar a conferência
            </h1>

            <p className="mt-2 text-sm text-[#D64545]">
              {erro || "Nenhum dado encontrado."}
            </p>

            <button
              onClick={voltar}
              className="mt-5 rounded-xl bg-[#0B3D2E] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#176B4D]"
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
    ehAuditor && statusAtual === "FINALIZADA" && divergenciasPendentes === 0;

  const podeReabrir =
    ehAuditor && (statusAtual === "FINALIZADA" || statusAtual === "REPROVADA");
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

  const menuItems = [
    {
      label: "Dashboard",
      href: "/dashboard",
      activeKey: "dashboard",
      icon: <DashboardIcon />,
    },
    {
      label: "Conferências",
      href: usuario?.perfil === "AUDITOR" ? "/dashboard/auditor" : "/dashboard",
      activeKey: "conferencias",
      icon: <ClipboardIcon />,
    },
    ...(ehAuditor
      ? [
          {
            label: "Auditoria",
            href: "/dashboard/auditor",
            activeKey: "auditoria",
            icon: <AuditIcon />,
          },
        ]
      : []),
  ];

  return (
    <AppShell
      usuario={usuario?.username}
      perfil={usuario?.perfil}
      menuItems={menuItems}
      activeKey="conferencias"
      onLogout={() => {
        localStorage.removeItem("token");
        localStorage.removeItem("usuario");
        localStorage.removeItem("perfil");

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
                className="mb-3 inline-flex items-center gap-2 text-xs font-medium text-[#64736B] transition hover:text-[#0B3D2E]"
              >
                <span>←</span>
                Voltar para conferências
              </button>

              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-[#0B3D2E] sm:text-3xl">
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

              <p className="mt-2 text-sm text-[#64736B]">
                Versão {dados.versao} • {dados.total_itens} itens
              </p>
            </div>

            <div className="rounded-2xl border border-[#DCE4DF] bg-white px-4 py-3 shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
              <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#64736B]">
                Perfil atual
              </p>

              <p className="mt-1 text-sm font-semibold text-[#0B3D2E]">
                {usuario?.perfil || "-"}
              </p>
            </div>
          </div>
        </section>

        {/* ===================================================
    AVISO DO AUDITOR
==================================================== */}

        {ehAuditor && statusAtual === "FINALIZADA" && (
          <div className="mb-6 rounded-2xl border border-[#3578B8]/30 bg-[#EEF5FB] p-5">
            <p className="font-semibold text-[#3578B8]">
              Conferência aguardando auditoria
            </p>

            <p className="mt-1 text-sm text-[#3578B8]">
              Revise os itens, divergências e justificativas antes de aprovar ou
              reprovar.
            </p>
          </div>
        )}

        {ehAuditor &&
          statusAtual === "FINALIZADA" &&
          divergenciasPendentes > 0 && (
            <div className="mb-6 rounded-2xl border border-[#D99000]/30 bg-[#FFF8E8] p-5">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#D99000]/15 text-xs font-bold text-[#A86F00]">
                  !
                </div>

                <div>
                  <p className="font-semibold text-[#A86F00]">
                    Auditoria aguardando justificativas
                  </p>

                  <p className="mt-1 text-sm leading-6 text-[#A86F00]">
                    Existem{" "}
                    <strong className="font-semibold text-[#A86F00]">
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
          <div className="mb-6 rounded-2xl border border-[#E87524]/30 bg-[#FFF3EA] p-5">
            <p className="font-semibold text-[#C95F16]">Conferência reaberta</p>

            <p className="mt-1 text-sm text-[#C95F16]">
              Esta é a versão {dados.versao}. As divergências desta versão
              precisam ser justificadas antes do fechamento.
            </p>
          </div>
        )}

        {/* ===================================================
            AÇÕES
        ==================================================== */}

        <div className="mb-6 rounded-2xl border border-[#DCE4DF] bg-white p-5 shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-[#0B3D2E]">
                Ações da conferência
              </p>

              <p className="mt-1 text-xs text-[#64736B]">
                As ações disponíveis dependem do perfil e do status.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              {podeImportarXml && (
                <label
                  className={[
                    "inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-[#DCE4DF] bg-white px-5 py-2.5 text-sm font-semibold text-[#0B3D2E] transition hover:border-[#176B4D] hover:bg-[#F6F7F5]",
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

                  <UploadIcon />
                  {importandoXml ? "Importando..." : "Importar XML"}
                </label>
              )}

              {podeFechar && (
                <button
                  onClick={fechar}
                  disabled={fechando}
                  className="rounded-xl bg-[#1DB954] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#18A64A] disabled:cursor-not-allowed disabled:opacity-50"
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
                      ? "cursor-not-allowed border border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B]"
                      : "bg-[#3578B8] text-white hover:bg-[#2B6398]",
                    "disabled:cursor-not-allowed disabled:opacity-60",
                  ].join(" ")}
                >
                  {processandoAuditoria
                    ? "Processando..."
                    : divergenciasPendentes > 0
                      ? `Aprovar (${divergenciasPendentes} pendente${divergenciasPendentes > 1 ? "s" : ""})`
                      : "Aprovar"}
                </button>
              )}

              {podeAuditar && (
                <button
                  onClick={reprovar}
                  disabled={processandoAuditoria}
                  className="rounded-xl bg-[#D64545] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#B93434] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {processandoAuditoria ? "Processando..." : "Reprovar"}
                </button>
              )}

              {podeReabrir && (
                <button
                  onClick={() => {
                    setErroAuditoria("");
                    setAbrirReabertura(true);
                  }}
                  disabled={processandoAuditoria}
                  className="rounded-xl border border-[#E87524]/40 bg-[#FFF3EA] px-5 py-2.5 text-sm font-semibold text-[#C95F16] transition hover:bg-[#FDE7D8] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reabrir
                </button>
              )}
            </div>
          </div>

          {erroFechamento && (
            <div className="mt-4 rounded-xl border border-[#D64545]/30 bg-[#FFF5F5] p-4 text-sm text-[#D64545]">
              {erroFechamento}
            </div>
          )}

          {erroImportacaoXml && (
            <div className="mt-4 rounded-xl border border-[#D64545]/30 bg-[#FFF5F5] p-4 text-sm text-[#D64545]">
              {erroImportacaoXml}
            </div>
          )}

          {erroAuditoria && (
            <div className="mt-4 rounded-xl border border-[#D64545]/30 bg-[#FFF5F5] p-4">
              <p className="font-semibold text-[#D64545]">
                Não foi possível processar a auditoria
              </p>

              <p className="mt-1 text-sm text-[#D64545]">{erroAuditoria}</p>
            </div>
          )}
        </div>

        {/* ===================================================
            FORMULÁRIO DE REABERTURA
        ==================================================== */}

        {abrirReabertura && (
          <div className="mb-6 rounded-2xl border border-[#E87524]/30 bg-white p-6 shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
            <h3 className="font-semibold text-[#C95F16]">
              Reabrir conferência
            </h3>

            <p className="mt-1 text-sm text-[#C95F16]">
              Informe obrigatoriamente o motivo da reabertura. Essa informação
              ficará registrada no histórico.
            </p>

            <textarea
              value={motivoReabertura}
              onChange={(event) => setMotivoReabertura(event.target.value)}
              placeholder="Ex.: Divergência encontrada durante a auditoria. Necessário realizar nova contagem."
              rows={4}
              disabled={processandoAuditoria}
              className="mt-4 w-full rounded-xl border border-[#DCE4DF] bg-[#F6F7F5] px-4 py-3 text-sm text-[#17231D] outline-none transition placeholder:text-[#64736B] focus:border-[#E87524] focus:ring-2 focus:ring-[#E87524]/15 disabled:opacity-50"
            />

            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => {
                  setAbrirReabertura(false);
                  setMotivoReabertura("");
                  setErroAuditoria("");
                }}
                disabled={processandoAuditoria}
                className="rounded-xl border border-[#DCE4DF] px-5 py-2.5 text-sm font-semibold text-[#0B3D2E] transition hover:bg-[#F6F7F5] disabled:opacity-50"
              >
                Cancelar
              </button>

              <button
                onClick={reabrir}
                disabled={processandoAuditoria}
                className="rounded-xl bg-[#E87524] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#C95F16] disabled:opacity-50"
              >
                {processandoAuditoria ? "Reabrindo..." : "Confirmar reabertura"}
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

        <div className="mt-6 rounded-2xl border border-[#DCE4DF] bg-white p-5 shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
          <div className="mb-2 flex justify-between text-sm">
            <span className="text-sm font-medium text-[#64736B]">
              Progresso da conferência
            </span>

            <span className="font-semibold text-[#0B3D2E]">{percentual}%</span>
          </div>

          <div className="h-2.5 overflow-hidden rounded-full bg-[#E7ECE9]">
            <div
              className="h-full rounded-full bg-[#1DB954] transition-all"
              style={{
                width: `${percentual}%`,
              }}
            />
          </div>
        </div>

        {/* ===================================================
            ITENS
        ==================================================== */}

        <section className="mt-8 overflow-hidden rounded-2xl border border-[#DCE4DF] bg-white shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
          {/* =====================================================
      CABEÇALHO
  ====================================================== */}

          <div className="border-b border-[#DCE4DF] px-6 py-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[#0B3D2E]">
                  Itens da conferência
                </h2>

                <p className="mt-1 text-xs text-[#64736B]">
                  Compare a quantidade esperada com a quantidade contada.
                </p>
              </div>

              <div className="text-xs text-[#64736B]">
                Exibindo{" "}
                <span className="font-semibold text-[#0B3D2E]">
                  {itensFiltrados.length}
                </span>{" "}
                de{" "}
                <span className="font-semibold text-[#0B3D2E]">
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
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#64736B]">
                  <SearchIcon />
                </span>

                <input
                  type="text"
                  value={buscaItens}
                  onChange={(event) => setBuscaItens(event.target.value)}
                  placeholder="Buscar por código ou produto..."
                  className="h-11 w-full rounded-xl border border-[#DCE4DF] bg-[#F6F7F5] pl-10 pr-4 text-sm text-[#17231D] outline-none transition placeholder:text-[#64736B] focus:border-[#176B4D] focus:bg-white focus:ring-2 focus:ring-[#176B4D]/10"
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
                className="h-11 rounded-xl border border-[#DCE4DF] bg-[#F6F7F5] px-4 text-sm text-[#17231D] outline-none transition focus:border-[#176B4D] focus:bg-white focus:ring-2 focus:ring-[#176B4D]/10"
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
                    ? "border-[#176B4D]/30 bg-[#EFFAF3] text-[#176B4D]"
                    : "border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B] hover:bg-white hover:text-[#0B3D2E]",
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
                    ? "border-[#D64545]/30 bg-[#FFF5F5] text-[#D64545]"
                    : "border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B] hover:bg-white hover:text-[#0B3D2E]",
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
                    ? "border-[#D99000]/30 bg-[#FFF8E8] text-[#A86F00]"
                    : "border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B] hover:bg-white hover:text-[#0B3D2E]",
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
                    ? "border-[#1DB954]/30 bg-[#EFFAF3] text-[#168C40]"
                    : "border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B] hover:bg-white hover:text-[#0B3D2E]",
                ].join(" ")}
              >
                Sem divergência{" "}
                {dados.itens.filter((item) => !item.divergente).length}
              </button>
            </div>
          </div>

          {dados.itens.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-[#64736B]">Nenhum item encontrado.</p>
            </div>
          ) : (
            <div className="max-h-[650px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-[#F6F7F5]">
                  <tr className="border-b border-[#DCE4DF] text-left text-xs uppercase tracking-wide text-[#64736B]">
                    <th className="px-6 py-4">Código</th>

                    <th className="px-6 py-4">Produto</th>

                    <th className="px-6 py-4 text-right">Esperado</th>

                    <th className="px-6 py-4 text-right">Contado</th>

                    <th className="px-6 py-4 text-right">Diferença</th>

                    <th className="px-6 py-4">Divergência</th>

                    <th className="px-6 py-4">Justificativa</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-[#DCE4DF]">
                  {itensFiltrados.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center">
                        <div className="mx-auto flex max-w-md flex-col items-center">
                          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-[#DCE4DF] bg-[#F6F7F5] text-[#64736B]">
                            <SearchIcon />
                          </div>

                          <p className="font-medium text-[#17231D]">
                            Nenhum item encontrado
                          </p>

                          <p className="mt-2 text-sm text-[#64736B]">
                            Tente alterar a busca ou o filtro selecionado.
                          </p>

                          <button
                            type="button"
                            onClick={() => {
                              setBuscaItens("");
                              setFiltroItens("TODOS");
                            }}
                            className="mt-4 rounded-lg border border-[#DCE4DF] px-4 py-2 text-xs font-semibold text-[#0B3D2E] transition hover:border-[#176B4D] hover:bg-[#F6F7F5]"
                          >
                            Limpar filtros
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    itensFiltrados.map((item) => {
                      const justificando =
                        justificativaAberta === item.divergencia_id;

                      return (
                        <tr
                          key={item.codigo}
                          className="transition hover:bg-[#F6F7F5]"
                        >
                          <td className="px-6 py-5 font-semibold text-[#17231D]">
                            {item.codigo}
                          </td>

                          <td className="px-6 py-5">
                            <p className="font-medium text-[#17231D]">
                              {item.descricao || "-"}
                            </p>
                          </td>
                          <td className="px-6 py-5 text-right">
                            <span
                              className={[
                                "inline-flex min-w-[52px] items-center justify-center rounded-lg px-2.5 py-1.5 font-bold",
                                item.diferenca < 0
                                  ? "bg-[#FFF5F5] text-[#D64545]"
                                  : item.diferenca > 0
                                    ? "bg-[#FFF3EA] text-[#C95F16]"
                                    : "bg-[#EFFAF3] text-[#168C40]",
                              ].join(" ")}
                            >
                              {item.diferenca > 0
                                ? `+${item.diferenca}`
                                : item.diferenca}
                            </span>
                          </td>

                          <td className="px-6 py-5 text-right">
                            <span
                              className={
                                item.divergente
                                  ? "font-bold text-[#D64545]"
                                  : "font-semibold text-[#168C40]"
                              }
                            >
                              {item.contado}
                            </span>
                          </td>

                          <td
                            className={`px-6 py-5 text-right font-semibold ${
                              item.diferenca < 0
                                ? "text-[#D64545]"
                                : item.diferenca > 0
                                  ? "text-[#C95F16]"
                                  : "text-[#168C40]"
                            }`}
                          >
                            {item.diferenca > 0
                              ? `+${item.diferenca}`
                              : item.diferenca}
                          </td>

                          <td className="px-6 py-5">
                            {item.divergente ? (
                              <div className="space-y-1.5">
                                <span className="inline-flex items-center rounded-lg border border-[#D64545]/30 bg-[#FFF5F5] px-2.5 py-1 text-xs font-semibold text-[#D64545]">
                                  Divergência
                                </span>

                                <p className="text-xs font-medium text-[#D64545]">
                                  {formatarTipo(item.tipo_divergencia)}
                                </p>

                                {item.divergencia_id && (
                                  <p className="text-xs text-[#64736B]">
                                    ID #{item.divergencia_id}
                                  </p>
                                )}
                              </div>
                            ) : (
                              <span className="inline-flex items-center rounded-lg border border-[#1DB954]/30 bg-[#EFFAF3] px-2.5 py-1 text-xs font-semibold text-[#168C40]">
                                ✓ Sem divergência
                              </span>
                            )}
                          </td>

                          <td className="min-w-[320px] px-6 py-5">
                            {!item.divergente ? (
                              <span className="text-[#64736B]">—</span>
                            ) : item.justificado ? (
                              <div className="rounded-lg border border-[#1DB954]/30 bg-[#EFFAF3] p-3">
                                <div className="flex items-center justify-between gap-3">
                                  <span className="font-semibold text-[#168C40]">
                                    ✓ Justificado
                                  </span>

                                  {item.justificativa_tipo && (
                                    <span className="text-xs text-[#64736B]">
                                      {formatarTipo(item.justificativa_tipo)}
                                    </span>
                                  )}
                                </div>

                                {item.justificativa_descricao && (
                                  <p className="mt-2 text-sm leading-5 text-[#64736B]">
                                    {item.justificativa_descricao}
                                  </p>
                                )}
                              </div>
                            ) : podeJustificar ? (
                              <div className="space-y-3">
                                {!justificando ? (
                                  <>
                                    <span className="text-[#A86F00]">
                                      Pendente
                                    </span>

                                    <div>
                                      <button
                                        onClick={() => abrirJustificativa(item)}
                                        className="rounded-lg border border-[#D99000]/35 bg-[#FFF8E8] px-3 py-2 text-xs font-semibold text-[#A86F00] transition hover:bg-[#FCEFCB]"
                                      >
                                        Justificar
                                      </button>
                                    </div>
                                  </>
                                ) : (
                                  <div className="rounded-xl border border-[#D99000]/30 bg-[#FFF8E8] p-4">
                                    <p className="mb-3 text-sm font-semibold text-[#A86F00]">
                                      Justificar divergência
                                    </p>

                                    <select
                                      value={justificativaTipo}
                                      onChange={(event) =>
                                        setJustificativaTipo(event.target.value)
                                      }
                                      disabled={processandoJustificativa}
                                      className="w-full rounded-lg border border-[#DCE4DF] bg-white px-3 py-2 text-sm text-[#17231D] outline-none focus:border-[#D99000] disabled:opacity-50"
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
                                      className="mt-3 w-full rounded-lg border border-[#DCE4DF] bg-white px-3 py-2 text-sm text-[#17231D] outline-none placeholder:text-[#64736B] focus:border-[#D99000] disabled:opacity-50"
                                    />

                                    {erroJustificativa && (
                                      <div className="rounded-lg border border-[#D64545]/30 bg-[#FFF5F5] p-3 text-xs text-[#D64545]">
                                        {erroJustificativa}
                                      </div>
                                    )}

                                    <div className="flex justify-end gap-2">
                                      <button
                                        onClick={cancelarJustificativa}
                                        disabled={processandoJustificativa}
                                        className="rounded-lg border border-[#DCE4DF] px-3 py-2 text-xs font-semibold text-[#0B3D2E] hover:bg-white disabled:opacity-50"
                                      >
                                        Cancelar
                                      </button>

                                      <button
                                        onClick={() => justificar(item)}
                                        disabled={processandoJustificativa}
                                        className="rounded-lg bg-[#1DB954] px-3 py-2 text-xs font-semibold text-white hover:bg-[#18A64A] disabled:opacity-50"
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
                                <span className="text-[#A86F00]">Pendente</span>

                                {ehAuditor && statusAtual === "FINALIZADA" && (
                                  <p className="mt-1 text-xs text-[#64736B]">
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
            className="flex w-full items-center justify-between rounded-2xl border border-[#DCE4DF] bg-white px-5 py-4 text-left shadow-[0_1px_2px_rgba(23,35,29,0.04)] transition hover:border-[#176B4D]/40 hover:shadow-sm"
          >
            <div>
              <p className="font-semibold text-[#0B3D2E]">
                Histórico da conferência
              </p>

              <p className="mt-1 text-xs text-[#64736B]">
                Consulte as alterações e decisões realizadas durante o processo.
              </p>
            </div>

            <span className="ml-4 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#0B3D2E] text-lg font-medium text-white">
              {mostrarHistorico ? "−" : "+"}
            </span>
          </button>

          {mostrarHistorico && (
            <div className="mt-3 overflow-hidden rounded-2xl border border-[#DCE4DF] bg-white shadow-[0_1px_2px_rgba(23,35,29,0.04)]">
              {timeline.length === 0 ? (
                <div className="px-6 py-10 text-center">
                  <p className="text-sm text-[#64736B]">
                    Nenhum evento registrado.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-[#DCE4DF]">
                  {timeline.map((evento, index) => (
                    <div key={`${evento.data}-${index}`} className="px-6 py-5">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="font-semibold text-[#0B3D2E]">
                            {evento.evento || evento.acao || "Evento"}
                          </p>

                          {evento.usuario && (
                            <p className="mt-1 text-xs text-[#64736B]">
                              Usuário: {evento.usuario}
                            </p>
                          )}

                          {evento.motivo && (
                            <p className="mt-2 text-sm text-[#64736B]">
                              {evento.motivo}
                            </p>
                          )}

                          {evento.descricao && (
                            <p className="mt-2 text-sm text-[#64736B]">
                              {evento.descricao}
                            </p>
                          )}
                        </div>

                        {evento.data && (
                          <p className="shrink-0 text-xs text-[#64736B]">
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
   ÍCONES DA NAVEGAÇÃO
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

function AuditIcon() {
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
      <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3Z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="7" />

      <path d="m20 20-4-4" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 16V4" />
      <path d="m8 8 4-4 4 4" />
      <path d="M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" />
    </svg>
  );
}

/* ============================================================
   RESUMO
============================================================ */

function Resumo({ titulo, valor }: { titulo: string; valor: number | string }) {
  const destaque =
    titulo === "Divergências" && Number(valor) > 0
      ? {
          borda: "border-[#D64545]/30",
          numero: "text-[#D64545]",
          ponto: "bg-[#D64545]",
        }
      : titulo === "Justificativas pendentes" && Number(valor) > 0
        ? {
            borda: "border-[#D99000]/30",
            numero: "text-[#A86F00]",
            ponto: "bg-[#D99000]",
          }
        : titulo === "Sem divergência" && Number(valor) > 0
          ? {
              borda: "border-[#1DB954]/30",
              numero: "text-[#168C40]",
              ponto: "bg-[#1DB954]",
            }
          : titulo === "Progresso"
            ? {
                borda: "border-[#1DB954]/30",
                numero: "text-[#168C40]",
                ponto: "bg-[#1DB954]",
              }
            : {
                borda: "border-[#DCE4DF]",
                numero: "text-[#17231D]",
                ponto: "bg-[#64736B]",
              };

  return (
    <div
      className={[
        "rounded-2xl border bg-white p-5 shadow-[0_1px_2px_rgba(23,35,29,0.04)]",
        "transition duration-200 hover:-translate-y-0.5 hover:shadow-md",
        destaque.borda,
      ].join(" ")}
    >
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64736B]">
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
