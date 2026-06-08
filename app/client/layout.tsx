"use client";

import { Sidebar } from "@/components/sidebar";
import { useApp } from "@/lib/app-context";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

function ClientLayoutContent({ children }: { children: React.ReactNode }) {
  const { role, setRole } = useApp();
  const pathname = usePathname();

  useEffect(() => {
    if (role === "internal" && pathname.startsWith("/client")) {
      setRole("client");
    }
  }, [role, pathname, setRole]);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="min-w-0 overflow-hidden pt-14 pb-16 lg:ml-64 lg:w-[calc(100%-16rem)] lg:pt-0 lg:pb-0">
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

