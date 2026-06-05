"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import type { UserRole, Meeting } from "@/lib/types";
import { mockMeetings } from "@/lib/mock-data";

const MEETINGS_STORAGE_KEY = "conprospeccion-demo-meetings";
const ROLE_STORAGE_KEY = "conprospeccion-demo-role";

interface AppContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  meetings: Meeting[];
  updateMeeting: (id: string, updates: Partial<Meeting>) => void;
  selectedMeetingId: string | null;
  setSelectedMeetingId: (id: string | null) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<UserRole>("client");
  const [meetings, setMeetings] = useState<Meeting[]>(mockMeetings);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [storageReady, setStorageReady] = useState(false);

  useEffect(() => {
    try {
      const savedRole = window.localStorage.getItem(ROLE_STORAGE_KEY) as UserRole | null;
      const savedMeetings = window.localStorage.getItem(MEETINGS_STORAGE_KEY);

      if (savedRole === "client" || savedRole === "internal") {
        setRole(savedRole);
      }

      if (savedMeetings) {
        setMeetings(JSON.parse(savedMeetings) as Meeting[]);
      }
    } catch {
      setMeetings(mockMeetings);
    } finally {
      setStorageReady(true);
    }
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    window.localStorage.setItem(ROLE_STORAGE_KEY, role);
  }, [role, storageReady]);

  useEffect(() => {
    if (!storageReady) return;
    window.localStorage.setItem(MEETINGS_STORAGE_KEY, JSON.stringify(meetings));
  }, [meetings, storageReady]);

  const updateMeeting = (id: string, updates: Partial<Meeting>) => {
    setMeetings((prev) =>
      prev.map((meeting) =>
        meeting.id === id ? { ...meeting, ...updates } : meeting
      )
    );
  };

  return (
    <AppContext.Provider
      value={{
        role,
        setRole,
        meetings,
        updateMeeting,
        selectedMeetingId,
        setSelectedMeetingId,
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

