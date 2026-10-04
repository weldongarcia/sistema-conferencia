export function limparSessao() {
  localStorage.removeItem("token");
  localStorage.removeItem("usuario");
  localStorage.removeItem("perfil");
}
