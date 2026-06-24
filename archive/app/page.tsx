"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useApp } from "@/lib/app-context";

export default function Home() {
  const router = useRouter();
  const { role } = useApp();

  useEffect(() => {
    if (role === "client") {
      router.push("/client/meeting-validation");
    } else {
      router.push("/internal/meeting-followup");
    }
  }, [role, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600 mx-auto mb-4">
          <span className="text-2xl font-bold text-white">CP</span>
        </div>
        <h1 className="text-xl font-semibold text-foreground">Conprospección OS</h1>
        <p className="text-sm text-muted-foreground mt-1">Loading...</p>
      </div>
    </div>
  );
}

