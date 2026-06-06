"use client";

import { useApp } from "@/lib/app-context";
import { Sidebar } from "@/components/sidebar";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function InternalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { role } = useApp();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (role === "client" && pathname.startsWith("/internal") && pathname !== "/internal/client-setup-os") {
      router.push("/client/meeting-validation");
    }
  }, [role, pathname, router]);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <main className="flex-1 ml-64">{children}</main>
    </div>
  );
}

