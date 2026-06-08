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
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="ml-64 min-w-0 w-[calc(100%-16rem)] overflow-hidden">{children}</main>
    </div>
  );
}

