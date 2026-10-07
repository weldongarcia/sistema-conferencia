import { ShieldCheck } from "lucide-react";

import ClipboardIcon from "../ui/ClipboardIcon";

/*
 * Fonte única do menu lateral.
 *
 * Cada perfil possui uma única tela de lista. Todas as
 * páginas (inclusive o detalhe da conferência) usam a
 * chave MENU_CONFERENCIAS para destacar esse item.
 */

export const MENU_CONFERENCIAS = "conferencias";

export function menuPorPerfil(perfil?: string) {
  if (perfil === "AUDITOR") {
    return [
      {
        label: "Auditoria",
        href: "/dashboard/auditor",
        activeKey: MENU_CONFERENCIAS,
        icon: <ShieldCheck size={18} strokeWidth={1.8} />,
      },
    ];
  }

  return [
    {
      label: "Conferências",
      href: "/dashboard",
      activeKey: MENU_CONFERENCIAS,
      icon: <ClipboardIcon />,
    },
  ];
}
