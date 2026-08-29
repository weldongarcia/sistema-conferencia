const API_URL = "http://127.0.0.1:8000";

export async function login(usuario: string, senha: string) {
  const response = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username: usuario,
      senha: senha,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail || "Usuário ou senha inválidos."
    );
  }

  return data;
}

export async function buscarUsuarioAtual(token: string) {
  const response = await fetch(`${API_URL}/usuario/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao buscar usuário: ${response.status}`
    );
  }

  return data;
}

export async function criarConferencia(token: string) {
  const response = await fetch(`${API_URL}/conferencias`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao criar conferência: ${response.status}`
    );
  }

  return data;
}

export async function buscarConferencias(token: string) {
  const response = await fetch(`${API_URL}/conferencias`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao buscar conferências: ${response.status}`
    );
  }

  return data;
}

export async function buscarConferencia(
  token: string,
  conferenciaId: number
) {
  const response = await fetch(
    `${API_URL}/conferencia/${conferenciaId}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao buscar conferência: ${response.status}`
    );
  }

  return data;
}

export async function fecharConferencia(
  token: string,
  conferenciaId: number
) {
  const response = await fetch(
    `${API_URL}/conferencia/${conferenciaId}/fechar`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao fechar conferência: ${response.status}`
    );
  }

  return data;
}

export async function aprovarConferencia(
  token: string,
  conferenciaId: number
) {
  const response = await fetch(
    `${API_URL}/conferencia/${conferenciaId}/aprovar`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao aprovar conferência: ${response.status}`
    );
  }

  return data;
}

export async function reprovarConferencia(
  token: string,
  conferenciaId: number
) {
  const response = await fetch(
    `${API_URL}/conferencia/${conferenciaId}/reprovar`,
    {
      method: "POST",
      headers: {
        Authorization: "Bearer ${token}",
        "Content-Type": "application/json",
      },
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao reprovar conferência: ${response.status}`
    );
  }

  return data;
}

export async function reabrirConferencia(
  token: string,
  conferenciaId: number,
  motivo: string
) {
  const response = await fetch(
    `${API_URL}/conferencia/${conferenciaId}/reabrir`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(motivo),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao reabrir conferência: ${response.status}`
    );
  }

  return data;
}

export async function justificarDivergencia(
  token: string,
  divergenciaId: number,
  justificativaTipo: string,
  justificativaDescricao: string
) {
  const response = await fetch(
    `${API_URL}/divergencias/${divergenciaId}/justificar`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        justificativa_tipo: justificativaTipo,
        justificativa_descricao:
          justificativaDescricao,
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    let mensagem = "Erro ao justificar divergência.";

    if (typeof data?.detail === "string") {
      mensagem = data.detail;
    }

    throw new Error(mensagem);
  }

  return data;
}

export async function buscarTimelineConferencia(
  token: string,
  conferenciaId: number
) {
  const response = await fetch(
    `${API_URL}/conferencia/${conferenciaId}/timeline`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        `Erro ao buscar histórico da conferência: ${response.status}`
    );
  }

  return data;
}