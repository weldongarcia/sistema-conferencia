import { ehSessaoExpirada } from "./api";

export function limparSessao() {
  localStorage.removeItem("token");
  localStorage.removeItem("usuario");
  localStorage.removeItem("perfil");
}

/*
 * Se o erro indicar sessão expirada (401), limpa a sessão
 * e redireciona para o login. Retorna true quando tratou o erro.
 */
export function tratarSessaoExpirada(
  error: unknown,
  router: { replace: (href: string) => void },
) {
  if (!ehSessaoExpirada(error)) return false;

  limparSessao();
  router.replace("/login");

  return true;
}
