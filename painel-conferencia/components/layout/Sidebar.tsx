"use client";

import Link from "next/link";

type MenuItem = {
  label: string;
  href: string;
  icon: React.ReactNode;
  activeKey?: string;
};

type SidebarProps = {
  items: MenuItem[];
  ativo?: string;
};

export default function Sidebar({ items, ativo }: SidebarProps) {
  return (
    <aside className="hidden w-[250px] shrink-0 border-r border-[#0B3D2E] bg-[#0B3D2E] lg:flex lg:flex-col">
      {/* =====================================================
          MARCA
      ====================================================== */}
      <div className="flex h-[76px] items-center border-b border-white/15 px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/20 bg-[#176B4D]">
            <span className="text-xl font-bold text-white">V</span>
          </div>

          <div>
            <p className="text-lg font-bold tracking-[0.16em] text-white">
              VÉRUM
            </p>

            <p className="text-[8px] tracking-[0.25em] text-[#B8D8C8]">
              SISTEMA DE CONFERÊNCIA
            </p>
          </div>
        </div>
      </div>

      {/* =====================================================
          NAVEGAÇÃO
      ====================================================== */}
      <nav className="flex-1 px-3 py-5">
        <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8FB5A4]">
          Navegação
        </p>

        <div className="space-y-1">
          {items.map((item) => {
            const chave = item.activeKey ?? item.href;
            const selecionado = ativo === chave;

            return (
              <Link
                key={`${item.label}-${item.href}`}
                href={item.href}
                className={[
                  "group flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition-all duration-200",

                  selecionado
                    ? "border border-[#176B4D] bg-[#176B4D] text-white shadow-sm"
                    : "border border-transparent text-[#C6DDD2] hover:bg-white/10 hover:text-white",
                ].join(" ")}
              >
                <span
                  className={[
                    "flex h-8 w-8 items-center justify-center rounded-lg transition",

                    selecionado
                      ? "bg-white/15 text-white"
                      : "bg-white/10 text-[#B8D8C8] group-hover:bg-white/15 group-hover:text-white",
                  ].join(" ")}
                >
                  {item.icon}
                </span>

                <span className="font-medium">{item.label}</span>

                {selecionado && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#1DB954]" />
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* =====================================================
          RODAPÉ
      ====================================================== */}
      <div className="border-t border-white/10 p-4">
        <div className="rounded-xl border border-white/15 bg-white/5 px-3 py-3">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#1DB954]" />

            <span className="text-xs text-[#B8D8C8]">Sistema operacional</span>
          </div>

          <p className="mt-2 text-[10px] text-[#8FB5A4]">Vérum • v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}
