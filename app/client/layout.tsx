"use client";

import { AppProvider } from "@/lib/app-context";
import { Sidebar } from "@/components/sidebar";
import { useApp } from "@/lib/app-context";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

function ClientLayoutContent({ children }: { children: React.ReactNode }) {
  const { role } = useApp();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (role === "internal" && pathname.startsWith("/client")) {
      router.push("/internal/meeting-followup");
    }
  }, [role, pathname, router]);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 ml-64">{children}</main>
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

