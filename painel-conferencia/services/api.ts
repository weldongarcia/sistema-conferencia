const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/* ============================================================
   ERROS
============================================================ */

export class SessaoExpiradaError extends Error {
  constructor(mensagem = "Sessão expirada. Faça login novamente.") {
    super(mensagem);
    this.name = "SessaoExpiradaError";
  }
}

export function ehSessaoExpirada(error: unknown) {
  return error instanceof SessaoExpiradaError;
}

function extrairMensagemErro(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;

  const detail = (data as { detail?: unknown }).detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  // Erros de validação do FastAPI (422): lista de { msg, loc, ... }
  if (Array.isArray(detail)) {
    const mensagens = detail
      .map((item) =>
        item && typeof item === "object" && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : null,
      )
      .filter(Boolean);

    if (mensagens.length > 0) {
      return mensagens.join(" ");
    }
  }

  return null;
}

/* ============================================================
   REQUISIÇÃO
============================================================ */

type OpcoesRequisicao = {
  method?: "GET" | "POST";
  token?: string;
  json?: unknown;
  formData?: FormData;
  // Em /login, 401 significa credenciais inválidas, não sessão expirada.
  tratar401ComoSessao?: boolean;
};

async function requisicao(
  caminho: string,
  opcoes: OpcoesRequisicao,
  mensagemPadrao: string,
) {
  const {
    method = "GET",
    token,
    json,
    formData,
    tratar401ComoSessao = true,
  } = opcoes;

  const headers: Record<string, string> = {};

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;

  if (formData) {
    body = formData;
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }

  let response: Response;

  try {
    response = await fetch(`${API_URL}${caminho}`, {
      method,
      headers,
      body,
      cache: method === "GET" ? "no-store" : undefined,
    });
  } catch {
    throw new Error(
      "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.",
    );
  }

  const texto = await response.text();

  let data: unknown = null;

  if (texto) {
    try {
      data = JSON.parse(texto);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && tratar401ComoSessao) {
      throw new SessaoExpiradaError();
    }

    throw new Error(
      extrairMensagemErro(data) ?? `${mensagemPadrao} (${response.status})`,
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return data as any;
}

/* ============================================================
   AUTENTICAÇÃO
============================================================ */

export async function login(usuario: string, senha: string) {
  return requisicao(
    "/login",
    {
      method: "POST",
      json: {
        username: usuario,
        senha: senha,
      },
      tratar401ComoSessao: false,
    },
    "Usuário ou senha inválidos.",
  );
}

export async function buscarUsuarioAtual(token: string) {
  return requisicao(
    "/usuario/me",
    { token },
    "Erro ao buscar usuário",
  );
}

/* ============================================================
   CONFERÊNCIAS
============================================================ */

export async function criarConferencia(token: string) {
  return requisicao(
    "/conferencias",
    { method: "POST", token, json: {} },
    "Erro ao criar conferência",
  );
}

export async function importarXml(
  token: string,
  conferenciaId: number,
  arquivo: File,
) {
  const formData = new FormData();

  formData.append("conferencia_id", String(conferenciaId));
  formData.append("file", arquivo);

  return requisicao(
    "/notas/importar-xml",
    { method: "POST", token, formData },
    "Erro ao importar XML",
  );
}

export async function buscarConferencias(token: string) {
  return requisicao(
    "/conferencias",
    { token },
    "Erro ao buscar conferências",
  );
}

export async function buscarConferencia(
  token: string,
  conferenciaId: number
) {
  return requisicao(
    `/conferencia/${conferenciaId}`,
    { token },
    "Erro ao buscar conferência",
  );
}

export async function fecharConferencia(
  token: string,
  conferenciaId: number
) {
  return requisicao(
    `/conferencia/${conferenciaId}/fechar`,
    { method: "POST", token },
    "Erro ao fechar conferência",
  );
}

export async function aprovarConferencia(
  token: string,
  conferenciaId: number
) {
  return requisicao(
    `/conferencia/${conferenciaId}/aprovar`,
    { method: "POST", token },
    "Erro ao aprovar conferência",
  );
}

export async function reprovarConferencia(
  token: string,
  conferenciaId: number
) {
  return requisicao(
    `/conferencia/${conferenciaId}/reprovar`,
    { method: "POST", token },
    "Erro ao reprovar conferência",
  );
}

export async function reabrirConferencia(
  token: string,
  conferenciaId: number,
  motivo: string
) {
  return requisicao(
    `/conferencia/${conferenciaId}/reabrir`,
    { method: "POST", token, json: motivo },
    "Erro ao reabrir conferência",
  );
}

export async function justificarDivergencia(
  token: string,
  divergenciaId: number,
  justificativaTipo: string,
  justificativaDescricao: string
) {
  return requisicao(
    `/divergencias/${divergenciaId}/justificar`,
    {
      method: "POST",
      token,
      json: {
        justificativa_tipo: justificativaTipo,
        justificativa_descricao: justificativaDescricao,
      },
    },
    "Erro ao justificar divergência",
  );
}

export async function buscarTimelineConferencia(
  token: string,
  conferenciaId: number
) {
  return requisicao(
    `/conferencia/${conferenciaId}/timeline`,
    { token },
    "Erro ao buscar histórico da conferência",
  );
}
