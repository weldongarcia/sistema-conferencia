"use client";

import { usePathname } from "next/navigation";

import Header from "./Header";
import Sidebar from "./Sidebar";

type MenuItem = {
  label: string;
  href: string;
  icon: React.ReactNode;
  activeKey?: string;
};

type AppShellProps = {
  children: React.ReactNode;
  usuario?: string;
  perfil?: string;
  menuItems: MenuItem[];
  activeKey?: string;
  onLogout?: () => void;
};

export default function AppShell({
  children,
  usuario,
  perfil,
  menuItems,
  activeKey,
  onLogout,
}: AppShellProps) {
  const pathname = usePathname();

  /*
   * Se a página informar explicitamente o activeKey,
   * ele tem prioridade.
   *
   * Caso contrário, tentamos identificar automaticamente
   * pela rota.
   */

  let ativo = activeKey;

  if (!ativo && pathname) {
    const itemExato = menuItems.find((item) => pathname === item.href);

    if (itemExato) {
      ativo = itemExato.activeKey ?? itemExato.href;
    } else {
      const itemCorrespondente = menuItems
        .filter((item) => item.href !== "/dashboard")
        .find((item) => pathname.startsWith(item.href));

      ativo = itemCorrespondente?.activeKey ?? itemCorrespondente?.href;
    }
  }

  return (
    <div className="flex min-h-screen bg-[#F6F7F5] text-[#17231D]">
      {/* =====================================================
          SIDEBAR
      ====================================================== */}

      <Sidebar items={menuItems} ativo={ativo} />

      {/* =====================================================
          ÁREA PRINCIPAL
      ====================================================== */}

      <div className="flex min-w-0 flex-1 flex-col">
        <Header usuario={usuario} perfil={perfil} onLogout={onLogout} />

        <main className="min-w-0 flex-1 bg-[#F6F7F5]">{children}</main>
      </div>
    </div>
  );
}
