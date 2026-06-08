"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useApp } from "@/lib/app-context";
import {
  Calendar,
  BarChart3,
  ClipboardCheck,
  Settings,
  Users,
  Briefcase,
  ChevronDown,
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
  { href: "/client/meeting-validation", label: "Validación de reuniones", icon: ClipboardCheck },
  { href: "/client/intelligence-insight", label: "Revenue Intelligence", icon: BarChart3 },
];

const internalNavItems = [
  { href: "/internal/sdr-leader-dashboard", label: "Panel líder SDR", icon: TrendingUp },
  { href: "/internal/meeting-followup", label: "Seguimiento reuniones", icon: Calendar },
  { href: "/internal/sdr-performance", label: "Performance SDR", icon: UserCheck },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { role, setRole } = useApp();
  const visibleRole = pathname.startsWith("/internal")
    ? "internal"
    : pathname.startsWith("/client")
      ? "client"
      : role;

  const navItems = visibleRole === "client" ? clientNavItems : internalNavItems;

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-card px-4 lg:hidden">
        <Link href={visibleRole === "client" ? "/client/meeting-validation" : "/internal/meeting-followup"} className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Briefcase className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <p className="text-sm font-semibold leading-4 text-foreground">Conprospección</p>
            <p className="text-[11px] leading-3 text-muted-foreground">
              {visibleRole === "client" ? "Portal cliente" : "Panel interno"}
            </p>
          </div>
        </Link>
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-xs font-medium text-foreground">
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
              Modo demo cliente
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                setRole("internal");
                router.push("/internal/meeting-followup");
              }}
            >
              <Users className="mr-2 h-4 w-4" />
              Modo demo interno
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t border-border bg-card px-2 py-1.5 lg:hidden">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-h-12 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-medium leading-tight transition-colors",
                isActive ? "bg-primary/10 text-primary" : "text-muted-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="max-w-full truncate">{mobileLabel(item.label)}</span>
            </Link>
          );
        })}
      </nav>

      <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 flex-col border-r border-border bg-card lg:flex">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-border px-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
          <Briefcase className="h-5 w-5 text-primary-foreground" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">Conprospección</p>
          <p className="text-xs text-muted-foreground">OS</p>
        </div>
      </div>

      {/* Role Switcher */}
      <div className="border-b border-border p-4">
        <DropdownMenu>
          <DropdownMenuTrigger className="flex w-full items-center justify-between rounded-lg bg-muted px-3 py-2 text-sm font-medium text-foreground hover:bg-muted/80 focus:outline-none">
            <div className="flex items-center gap-2">
              {visibleRole === "client" ? (
                <Building2 className="h-4 w-4" />
              ) : (
                <Users className="h-4 w-4" />
              )}
              <span>{visibleRole === "client" ? "Modo demo cliente" : "Modo demo interno"}</span>
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
              Modo demo cliente
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                setRole("internal");
                router.push("/internal/meeting-followup");
              }}
            >
              <Users className="mr-2 h-4 w-4" />
              Modo demo interno
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <p className="mt-2 text-xs text-muted-foreground">Datos demo · Prototipo funcional</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Client info at bottom */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <span className="text-xs font-semibold text-primary">GBS</span>
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-foreground">GBS Logistics</p>
            <p className="text-xs text-muted-foreground">
              {visibleRole === "client" ? "Portal cliente" : "Panel interno"}
            </p>
          </div>
          <Settings className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
      </aside>
    </>
  );
}

function mobileLabel(label: string) {
  if (label === "Resumen de performance") return "Resumen";
  if (label === "Validación de reuniones") return "Validación";
  if (label === "Revenue Intelligence") return "Intel.";
  if (label === "Panel líder SDR") return "Líder";
  if (label === "Seguimiento reuniones") return "Seguimiento";
  if (label === "Performance SDR") return "SDR";
  return label;
}

