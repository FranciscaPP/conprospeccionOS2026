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
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="ml-64 min-w-0 w-[calc(100%-16rem)] overflow-hidden">{children}</main>
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

