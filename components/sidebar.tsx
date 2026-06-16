"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useApp } from "@/lib/app-context";
import {
  Calendar,
  BarChart3,
  ClipboardCheck,
  Users,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Building2,
  LayoutDashboard,
  TrendingUp,
  UserCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const clientNavItems = [
  { href: "/client/performance-overview", label: "Resumen de performance", icon: LayoutDashboard },
  { href: "/client/meeting-validation", label: "Avance reuniones", icon: ClipboardCheck },
  { href: "/client/intelligence-insight", label: "Revenue Intelligence", icon: BarChart3 },
];

const internalNavItems = [
  { href: "/internal/sdr-leader-dashboard", label: "Panel líder SDR", icon: TrendingUp },
  { href: "/internal/meeting-followup", label: "Seguimiento reuniones", icon: Calendar },
  { href: "/internal/sdr-performance", label: "Performance SDR", icon: UserCheck },
];

const ACTIVE_NAV = "bg-[rgba(255,215,0,0.14)] text-[#ffd700]";
const INACTIVE_NAV = "text-[#aaaaa3] hover:bg-white/5 hover:text-white";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { role, setRole, sidebarCollapsed, setSidebarCollapsed } = useApp();
  const visibleRole = pathname.startsWith("/internal")
    ? "internal"
    : pathname.startsWith("/client")
      ? "client"
      : role;

  const navItems = visibleRole === "client" ? clientNavItems : internalNavItems;
  const subtitle = visibleRole === "client" ? "Portal cliente" : "Panel interno";

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center justify-between border-b border-white/10 bg-[#2b2b2b] px-4 lg:hidden">
        <Link
          href={visibleRole === "client" ? "/client/meeting-validation" : "/internal/meeting-followup"}
          className="flex items-center gap-2"
        >
          <Image src="/conprospeccion-isotype.png" alt="Conprospección" width={32} height={26} priority />
          <div>
            <p className="text-sm font-semibold leading-4 text-white">Conprospección</p>
            <p className="text-[11px] leading-3 text-[#9a9a93]">{subtitle}</p>
          </div>
        </Link>
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-xs font-medium text-[#e9e9e6] hover:bg-white/10">
            {visibleRole === "client" ? <Building2 className="h-4 w-4" /> : <Users className="h-4 w-4" />}
            <ChevronDown className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuItem
              onClick={() => {
                setRole("client");
                router.push("/client/meeting-validation");
              }}
            >
              <Building2 className="mr-2 h-4 w-4" />
              Vista cliente
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                setRole("internal");
                router.push("/internal/meeting-followup");
              }}
            >
              <Users className="mr-2 h-4 w-4" />
              Vista interna
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t border-white/10 bg-[#2b2b2b] px-2 py-1.5 lg:hidden">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-h-12 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-medium leading-tight transition-colors",
                isActive ? "text-[#ffd700]" : "text-[#aaaaa3]"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="max-w-full truncate">{mobileLabel(item.label)}</span>
            </Link>
          );
        })}
      </nav>

      <aside
        className={cn(
          "fixed left-0 top-0 z-40 hidden h-screen flex-col border-r border-black/20 bg-[#2b2b2b] text-[#e9e9e6] transition-[width] duration-200 lg:flex",
          sidebarCollapsed ? "w-16" : "w-64"
        )}
      >
        <button
          type="button"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          aria-label={sidebarCollapsed ? "Expandir menú" : "Contraer menú"}
          className="absolute -right-3 top-[68px] z-50 grid h-6 w-6 place-items-center rounded-full border border-black/20 bg-[#2b2b2b] text-[#e9e9e6] shadow-md transition-colors hover:bg-[#3a3a3a]"
        >
          {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
        {/* Logo */}
        <div
          className={cn(
            "flex h-16 items-center gap-2.5 border-b border-white/10",
            sidebarCollapsed ? "justify-center px-0" : "px-4"
          )}
        >
          <Image
            src="/conprospeccion-isotype.png"
            alt="Conprospección"
            width={sidebarCollapsed ? 30 : 36}
            height={sidebarCollapsed ? 24 : 29}
            priority
          />
          {!sidebarCollapsed && (
            <div>
              <p className="text-[13px] font-semibold leading-4 text-white">Conprospección</p>
              <p className="text-[11px] leading-3 text-[#9a9a93]">{subtitle}</p>
            </div>
          )}
        </div>

        {/* Role Switcher */}
        {!sidebarCollapsed && (
          <div className="border-b border-white/10 p-4">
            <DropdownMenu>
              <DropdownMenuTrigger className="flex w-full items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm font-medium text-[#e9e9e6] hover:bg-white/10 focus:outline-none">
                <div className="flex items-center gap-2">
                  {visibleRole === "client" ? <Building2 className="h-4 w-4" /> : <Users className="h-4 w-4" />}
                  <span>{visibleRole === "client" ? "Vista cliente" : "Vista interna"}</span>
                </div>
                <ChevronDown className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuItem
                  onClick={() => {
                    setRole("client");
                    router.push("/client/meeting-validation");
                  }}
                >
                  <Building2 className="mr-2 h-4 w-4" />
                  Vista cliente
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setRole("internal");
                    router.push("/internal/meeting-followup");
                  }}
                >
                  <Users className="mr-2 h-4 w-4" />
                  Vista interna
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={sidebarCollapsed ? item.label : undefined}
                className={cn(
                  "flex items-center rounded-lg text-sm font-medium transition-colors",
                  sidebarCollapsed ? "justify-center px-0 py-3" : "gap-3 px-3 py-2.5",
                  isActive ? ACTIVE_NAV : INACTIVE_NAV
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!sidebarCollapsed && item.label}
              </Link>
            );
          })}
        </nav>

      </aside>
    </>
  );
}

function mobileLabel(label: string) {
  if (label === "Resumen de performance") return "Resumen";
  if (label === "Avance reuniones") return "Avance";
  if (label === "Revenue Intelligence") return "Intel.";
  if (label === "Panel líder SDR") return "Líder";
  if (label === "Seguimiento reuniones") return "Seguimiento";
  if (label === "Performance SDR") return "SDR";
  return label;
}
