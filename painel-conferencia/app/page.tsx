"use client";

import { FormEvent, useState } from "react";
import {
   login,
  buscarUsuarioAtual,
 } from "../services/api";

export default function Home() {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

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

      console.log("LOGIN REALIZADO:", data);

      /*
       * Vamos verificar o formato real da resposta
       * antes de definir definitivamente a sessão.
       */
      const token =
        data?.access_token ??
        data?.token ??
        data?.accessToken;

      if (!token) {
        console.log("Resposta completa do login:", data);
        throw new Error(
          "Login realizado, mas o token não foi encontrado na resposta."
        );
      }

      localStorage.setItem("token", token);
      localStorage.setItem("usuario", usuario.trim());

      const usuarioAtual = await buscarUsuarioAtual(token);

        localStorage.setItem(
          "perfil",
          usuarioAtual.perfil
        );

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
          : "Não foi possível realizar o login."
      );
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center px-6">
      <div className="w-full max-w-md">

        {/* LOGO / IDENTIDADE */}
        <div className="text-center mb-8">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-900">
            <span className="text-3xl">✓</span>
          </div>

          <h1 className="text-3xl font-bold text-white">
            Sistema de Conferência
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Painel de controle e auditoria
          </p>
        </div>

        {/* CARD LOGIN */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">

          <div className="mb-6">
            <h2 className="text-xl font-semibold text-white">
              Entrar
            </h2>

            <p className="mt-1 text-sm text-slate-400">
              Acesse o painel administrativo
            </p>
          </div>

          <form onSubmit={realizarLogin} className="space-y-5">

            {/* USUÁRIO */}
            <div>
              <label
                htmlFor="usuario"
                className="mb-2 block text-sm font-medium text-slate-300"
              >
                Usuário
              </label>

              <input
                id="usuario"
                type="text"
                value={usuario}
                onChange={(event) => setUsuario(event.target.value)}
                autoComplete="username"
                disabled={carregando}
                placeholder="Digite seu usuário"
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-900 disabled:opacity-50"
              />
            </div>

            {/* SENHA */}
            <div>
              <label
                htmlFor="senha"
                className="mb-2 block text-sm font-medium text-slate-300"
              >
                Senha
              </label>

              <input
                id="senha"
                type="password"
                value={senha}
                onChange={(event) => setSenha(event.target.value)}
                autoComplete="current-password"
                disabled={carregando}
                placeholder="Digite sua senha"
                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-900 disabled:opacity-50"
              />
            </div>

            {/* ERRO */}
            {erro && (
              <div className="rounded-xl border border-red-900 bg-red-950/50 px-4 py-3 text-sm text-red-300">
                {erro}
              </div>
            )}

            {/* BOTÃO */}
            <button
              type="submit"
              disabled={carregando}
              className="w-full rounded-xl bg-emerald-800 px-4 py-3 font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {carregando ? "ENTRANDO..." : "ENTRAR"}
            </button>

          </form>
        </div>

        <p className="mt-6 text-center text-xs text-slate-600">
          Sistema de Conferência
        </p>

      </div>
    </main>
  );
}