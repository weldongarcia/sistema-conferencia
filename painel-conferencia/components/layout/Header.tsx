"use client";

import { User } from "lucide-react";

type HeaderProps = {
  usuario?: string;
  perfil?: string;
  onLogout?: () => void;
};

export default function Header({ usuario, perfil, onLogout }: HeaderProps) {
  return (
    <header className="h-[76px] shrink-0 border-b border-[#DCE4DF] bg-white">
      <div className="flex h-full items-center justify-between px-5 sm:px-8">
        {/* ===================================================
            TÍTULO MOBILE
        ==================================================== */}
        <div className="flex items-center gap-3 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#0B3D2E]">
            <span className="text-xl font-bold text-white">V</span>
          </div>

          <span className="text-lg font-bold tracking-[0.14em] text-[#0B3D2E]">
            VÉRUM
          </span>
        </div>

        {/* ===================================================
            ESPAÇO DESKTOP
        ==================================================== */}
        <div className="hidden lg:block" />

        {/* ===================================================
            USUÁRIO
        ==================================================== */}
        <div className="flex items-center gap-4">
          {/* Informações do usuário */}
          <div className="hidden text-right sm:block">
            <p className="text-sm font-semibold text-[#0B3D2E]">
              {usuario || "Usuário"}
            </p>

            <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#64736B]">
              {perfil || "Usuário"}
            </p>
          </div>

          {/* Avatar */}
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#0B3D2E] text-white">
            <User size={19} strokeWidth={1.8} className="text-white" />
          </div>

          {/* Separador */}
          <div className="hidden h-8 w-px bg-[#DCE4DF] sm:block" />

          {/* Logout */}
          <button
            type="button"
            onClick={onLogout}
            className="flex h-10 items-center gap-2 rounded-lg border border-[#DCE4DF] bg-white px-3 text-sm font-medium text-[#17231D] transition hover:border-[#D64545] hover:bg-[#FFF5F5] hover:text-[#D64545]"
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10 17l5-5-5-5" />
              <path d="M15 12H3" />
              <path d="M21 19V5a2 2 0 0 0-2-2h-5" />
            </svg>

            <span className="hidden sm:inline">Sair</span>
          </button>
        </div>
      </div>
    </header>
  );
}
