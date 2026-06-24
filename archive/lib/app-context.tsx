"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import type { UserRole, Meeting } from "@/lib/types";
import { normalizeMeeting, updateMeetingWithRules } from "@/lib/meeting-rules";
import type { MeetingsPayload } from "@/lib/supabase-meetings";

const ROLE_STORAGE_KEY = "conprospeccion-demo-role";

interface AppContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  meetings: Meeting[];
  meetingsLoading: boolean;
  meetingsError: string | null;
  meetingsMeta: MeetingsPayload["meta"] | null;
  refreshMeetings: () => Promise<void>;
  updateMeeting: (id: string, updates: Partial<Meeting>) => void;
  selectedMeetingId: string | null;
  setSelectedMeetingId: (id: string | null) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<UserRole>("client");
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [meetingsLoading, setMeetingsLoading] = useState(true);
  const [meetingsError, setMeetingsError] = useState<string | null>(null);
  const [meetingsMeta, setMeetingsMeta] = useState<MeetingsPayload["meta"] | null>(null);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [storageReady, setStorageReady] = useState(false);

  const refreshMeetings = async () => {
    setMeetingsLoading(true);
    setMeetingsError(null);
    try {
      const response = await fetch("/api/internal/meetings", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "No se pudieron cargar reuniones reales.");
      }
      setMeetings((payload.meetings as Meeting[]).map(normalizeMeeting));
      setMeetingsMeta((payload as MeetingsPayload).meta);
    } catch (error) {
      setMeetings([]);
      setMeetingsMeta(null);
      setMeetingsError(error instanceof Error ? error.message : "Error cargando reuniones reales.");
    } finally {
      setMeetingsLoading(false);
    }
  };

  useEffect(() => {
    try {
      const savedRole = window.localStorage.getItem(ROLE_STORAGE_KEY) as UserRole | null;

      if (savedRole === "client" || savedRole === "internal") {
        setRole(savedRole);
      }
    } catch {
      setMeetings([]);
    } finally {
      setStorageReady(true);
    }
  }, []);

  useEffect(() => {
    refreshMeetings();
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    window.localStorage.setItem(ROLE_STORAGE_KEY, role);
  }, [role, storageReady]);

  const updateMeeting = (id: string, updates: Partial<Meeting>) => {
    setMeetings((prev) =>
      prev.map((meeting) =>
        meeting.id === id ? updateMeetingWithRules(meeting, updates) : meeting
      )
    );
  };

  return (
    <AppContext.Provider
      value={{
        role,
        setRole,
        meetings,
        meetingsLoading,
        meetingsError,
        meetingsMeta,
        refreshMeetings,
        updateMeeting,
        selectedMeetingId,
        setSelectedMeetingId,
        sidebarCollapsed,
        setSidebarCollapsed,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
}

