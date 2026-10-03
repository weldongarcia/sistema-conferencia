"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, CircleAlert } from "lucide-react";

import { login, buscarUsuarioAtual } from "../../services/api";

export default function LoginPage() {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);

  async function realizarLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (carregando) return;

    setErro("");

    if (!usuario.trim()) {
      setErro("Informe o usuário.");
      return;
    }

    if (!senha) {
      setErro("Informe a senha.");
      return;
    }

    setCarregando(true);

    try {
      const data = await login(usuario.trim(), senha);

      const token = data?.access_token ?? data?.token ?? data?.accessToken;

      if (!token) {
        console.log("Resposta completa do login:", data);

        throw new Error(
          "Login realizado, mas o token não foi encontrado na resposta.",
        );
      }

      localStorage.setItem("token", token);
      localStorage.setItem("usuario", usuario.trim());

      const usuarioAtual = await buscarUsuarioAtual(token);

      localStorage.setItem("perfil", usuarioAtual.perfil);

      if (usuarioAtual.perfil === "AUDITOR") {
        window.location.href = "/dashboard/auditor";
      } else {
        window.location.href = "/dashboard";
      }
    } catch (error) {
      console.error(error);

      setErro(
        error instanceof Error
          ? error.message
          : "Não foi possível realizar o login.",
      );
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#050B0D] text-white">
      {/* =====================================================
          FUNDO VÉRUM
      ====================================================== */}

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Iluminação central */}
        <div className="absolute left-1/2 top-[-280px] h-[700px] w-[1000px] -translate-x-1/2 rounded-full bg-emerald-900/15 blur-3xl" />

        {/* V esquerdo */}
        <div className="absolute -left-52 bottom-[-300px] select-none text-[680px] font-black leading-none text-emerald-950/30">
          V
        </div>

        {/* V direito */}
        <div className="absolute -right-52 top-[-260px] select-none text-[680px] font-black leading-none text-emerald-950/20">
          V
        </div>

        {/* Linhas laterais */}
        <div className="absolute left-0 top-0 h-full w-px bg-gradient-to-b from-transparent via-emerald-900/30 to-transparent" />

        <div className="absolute right-0 top-0 h-full w-px bg-gradient-to-b from-transparent via-emerald-900/20 to-transparent" />
      </div>

      {/* =====================================================
          CONTEÚDO
      ====================================================== */}

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-5 py-12">
        {/* ===================================================
            MARCA
        ==================================================== */}

        <header className="mb-10 text-center">
          {/* Símbolo */}
          <div className="mx-auto mb-6 flex h-[76px] w-[76px] items-center justify-center rounded-2xl border border-emerald-700/60 bg-emerald-950/80 shadow-[0_0_40px_rgba(16,185,129,0.12)]">
            <span className="text-[46px] font-bold leading-none text-emerald-300">
              V
            </span>
          </div>

          {/* Nome */}
          <h1 className="text-[42px] font-bold tracking-[0.20em] text-white sm:text-[46px]">
            VÉRUM
          </h1>

          <div className="mt-3 text-[11px] font-medium tracking-[0.40em] text-slate-400">
            SISTEMA DE CONFERÊNCIA
          </div>

          <p className="mt-5 text-sm text-slate-400">
            Controle. Precisão. Confiança.
          </p>
        </header>

        {/* ===================================================
            LOGIN
        ==================================================== */}

        <section className="w-full max-w-[540px]">
          <div className="rounded-2xl border border-slate-700/80 bg-[#0B141B]/95 p-8 shadow-[0_25px_90px_rgba(0,0,0,0.50)] backdrop-blur-xl sm:p-10">
            {/* Cabeçalho */}
            <div className="mb-8">
              <h2 className="text-[25px] font-semibold tracking-tight text-white">
                Acesso ao sistema
              </h2>

              <p className="mt-2 text-sm text-slate-400">
                Informe suas credenciais para continuar.
              </p>
            </div>

            <form onSubmit={realizarLogin} className="space-y-6">
              {/* =================================================
                  USUÁRIO
              ================================================== */}

              <div>
                <label
                  htmlFor="usuario"
                  className="mb-2.5 block text-sm font-medium text-slate-300"
                >
                  Usuário
                </label>

                <div className="relative">
                  {/* Ícone */}
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-500">
                    <svg
                      width="21"
                      height="21"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <circle cx="12" cy="7" r="4" />

                      <path d="M5.5 21a6.5 6.5 0 0 1 13 0" />
                    </svg>
                  </div>

                  <input
                    id="usuario"
                    type="text"
                    value={usuario}
                    onChange={(event) => setUsuario(event.target.value)}
                    autoComplete="username"
                    disabled={carregando}
                    placeholder="Digite seu usuário"
                    className="h-[52px] w-full rounded-xl border border-slate-700 bg-[#081016] pl-12 pr-4 text-[15px] text-white outline-none transition duration-200 placeholder:text-slate-600 hover:border-slate-600 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-900/40 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </div>
              </div>

              {/* =================================================
                  SENHA
              ================================================== */}

              <div>
                <label
                  htmlFor="senha"
                  className="mb-2.5 block text-sm font-medium text-slate-300"
                >
                  Senha
                </label>

                <div className="relative">
                  {/* Cadeado */}
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-500">
                    <svg
                      width="21"
                      height="21"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <rect x="4" y="10" width="16" height="11" rx="2" />

                      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
                    </svg>
                  </div>

                  <input
                    id="senha"
                    type={mostrarSenha ? "text" : "password"}
                    value={senha}
                    onChange={(event) => setSenha(event.target.value)}
                    autoComplete="current-password"
                    disabled={carregando}
                    placeholder="Digite sua senha"
                    className="h-[52px] w-full rounded-xl border border-slate-700 bg-[#081016] pl-12 pr-14 text-[15px] text-white outline-none transition duration-200 placeholder:text-slate-600 hover:border-slate-600 focus:border-emerald-600 focus:ring-2 focus:ring-emerald-900/40 disabled:cursor-not-allowed disabled:opacity-50"
                  />

                  {/* Visualizar senha */}
                  <button
                    type="button"
                    onClick={() => setMostrarSenha((valor) => !valor)}
                    disabled={carregando}
                    aria-label={
                      mostrarSenha ? "Ocultar senha" : "Visualizar senha"
                    }
                    title={mostrarSenha ? "Ocultar senha" : "Visualizar senha"}
                    className="absolute inset-y-0 right-0 flex w-[52px] items-center justify-center text-slate-500 transition hover:text-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {mostrarSenha ? (
                      /* Olho aberto */
                      <svg
                        width="21"
                        height="21"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />

                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    ) : (
                      /* Olho riscado */
                      <svg
                        width="21"
                        height="21"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M3 3l18 18" />

                        <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />

                        <path d="M9.9 4.3A10.8 10.8 0 0 1 12 4c6.5 0 10 8 10 8a18.2 18.2 0 0 1-3.1 4.3" />

                        <path d="M6.2 6.2C3.6 8.2 2 12 2 12s3.5 8 10 8a9.8 9.8 0 0 0 4.1-.9" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* =================================================
                  ERRO
              ================================================== */}

              {erro && (
                <div className="rounded-xl border border-red-900/70 bg-red-950/30 px-4 py-3.5">
                  <div className="flex items-start gap-3">
                    <CircleAlert
                      className="mt-0.5 shrink-0 text-red-400"
                      size={19}
                    />

                    <div>
                      <p className="text-sm font-medium text-red-300">
                        Não foi possível entrar
                      </p>

                      <p className="mt-1 text-xs leading-relaxed text-red-400/80">
                        {erro}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* =================================================
                  BOTÃO
              ================================================== */}

              <button
                type="submit"
                disabled={carregando}
                className="group flex h-[52px] w-full items-center justify-center gap-3 rounded-xl bg-emerald-700 px-4 text-[15px] font-semibold text-white shadow-lg shadow-emerald-950/30 transition duration-200 hover:bg-emerald-600 hover:shadow-emerald-900/30 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {carregando ? (
                  <>
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    ENTRANDO...
                  </>
                ) : (
                  <>
                    ENTRAR
                    <ArrowRight
                      className="transition-transform duration-200 group-hover:translate-x-1"
                      size={20}
                    />
                  </>
                )}
              </button>
            </form>

            {/* =================================================
                INFORMAÇÕES
            ================================================== */}

            <div className="mt-8 flex items-center justify-between border-t border-slate-800 pt-5 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <svg
                  width="16"
                  height="16"
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

                <span>Acesso seguro</span>
              </div>

              <span>Vérum • v1.0.0</span>
            </div>
          </div>

          {/* =================================================
              FRASE
          ================================================== */}

          <div className="mt-8 text-center">
            <div className="mx-auto mb-3 h-px w-16 bg-emerald-700/60" />

            <p className="text-xs uppercase tracking-[0.30em] text-slate-500">
              Estoque real. Decisões mais seguras.
            </p>
          </div>
        </section>

        {/* ===================================================
            RODAPÉ
        ==================================================== */}

        <footer className="mt-8 text-center text-xs text-slate-600">
          © {new Date().getFullYear()} Vérum — Sistema de Conferência
        </footer>
      </div>
    </main>
  );
}
