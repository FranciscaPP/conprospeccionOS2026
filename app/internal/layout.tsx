"use client";

import { useApp } from "@/lib/app-context";
import { Sidebar } from "@/components/sidebar";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

export default function InternalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { role, setRole, sidebarCollapsed } = useApp();
  const pathname = usePathname();

  useEffect(() => {
    if (role === "client" && pathname.startsWith("/internal")) {
      setRole("internal");
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

