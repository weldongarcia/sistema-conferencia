/*
 * Quantidades chegam do backend como float. Formata em pt-BR
 * e elimina ruído de ponto flutuante (ex.: 0.30000000000000004).
 */
export function formatarQuantidade(valor: number) {
  return valor.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
}
