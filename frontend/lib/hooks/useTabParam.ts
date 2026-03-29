"use client";

import { useSearchParams, useRouter, usePathname } from "next/navigation";

/**
 * Lê o tab ativo da URL (?tab=xxx) e retorna um setter que atualiza a URL.
 * Requer que o componente que usa este hook esteja dentro de um <Suspense>.
 */
export function useTabParam(defaultTab: string): [string, (tab: string) => void] {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const activeTab = searchParams.get("tab") ?? defaultTab;

  function setTab(tab: string) {
    router.push(`${pathname}?tab=${tab}`, { scroll: false });
  }

  return [activeTab, setTab];
}
