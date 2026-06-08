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
  const { role, setRole } = useApp();
  const pathname = usePathname();

  useEffect(() => {
    if (role === "client" && pathname.startsWith("/internal")) {
      setRole("internal");
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

