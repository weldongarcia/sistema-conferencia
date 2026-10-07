/*
 * Quantidades chegam do backend como float. Formata em pt-BR
 * e elimina ruído de ponto flutuante (ex.: 0.30000000000000004).
 */
export function formatarQuantidade(valor: number) {
  return valor.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
}

/*
 * O backend grava datas em UTC (datetime.utcnow) e as serializa
 * sem fuso. Sem o sufixo, o navegador as interpretaria como hora
 * local. Datas que já trazem fuso são mantidas.
 */
export function formatarDataHora(data: string) {
  const temFuso = /(Z|[+-]\d{2}:?\d{2})$/i.test(data);

  return new Date(temFuso ? data : `${data}Z`).toLocaleString("pt-BR");
}
