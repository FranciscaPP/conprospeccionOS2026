"use client";

import { Sidebar } from "@/components/sidebar";
import { useApp } from "@/lib/app-context";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

function ClientLayoutContent({ children }: { children: React.ReactNode }) {
  const { role, setRole, sidebarCollapsed } = useApp();
  const pathname = usePathname();

  useEffect(() => {
    if (role === "internal" && pathname.startsWith("/client")) {
      setRole("client");
    }
  }, [role, pathname, setRole]);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main
        className={`min-w-0 overflow-hidden pt-14 pb-16 transition-[margin,width] duration-200 lg:pt-0 lg:pb-0 ${
          sidebarCollapsed ? "lg:ml-16 lg:w-[calc(100%-4rem)]" : "lg:ml-64 lg:w-[calc(100%-16rem)]"
        }`}
      >
        {children}
      </main>
    </div>
  );
}

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ClientLayoutContent>{children}</ClientLayoutContent>;
}

