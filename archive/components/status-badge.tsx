import { cn } from "@/lib/utils";
import type {
  CPValidation,
  ClientValidation,
  FinalValidation,
  CommercialStatus,
  MeetingStatus,
  MeetingFlowStatus,
} from "@/lib/types";

type StatusType = CPValidation | ClientValidation | FinalValidation | CommercialStatus | MeetingStatus | MeetingFlowStatus;

interface StatusBadgeProps {
  status: StatusType;
  label: string;
  size?: "sm" | "md";
}

type Tone = "ok" | "warn" | "bad" | "rev" | "neutral";

const toneStyles: Record<Tone, { pill: string; dot: string }> = {
  ok: { pill: "bg-[var(--ok-bg)] text-[var(--ok-ink)]", dot: "var(--ok)" },
  warn: { pill: "bg-[var(--warn-bg)] text-[var(--warn-ink)]", dot: "var(--warn)" },
  bad: { pill: "bg-[var(--bad-bg)] text-[var(--bad-ink)]", dot: "var(--bad)" },
  rev: { pill: "bg-[var(--rev-bg)] text-[var(--rev-ink)]", dot: "var(--rev)" },
  neutral: { pill: "bg-[#efefec] text-[#555]", dot: "#9a9a92" },
};

const getTone = (status: StatusType): Tone => {
  if (
    status === "valid_cp" ||
    status === "valid_client" ||
    status === "final_valid" ||
    status === "evaluation_closed_valid" ||
    status === "completed" ||
    status === "client_won"
  ) {
    return "ok";
  }

  if (
    status === "in_dispute" ||
    status === "under_review" ||
    status === "requires_review" ||
    status === "client_requests_review"
  ) {
    return "rev";
  }

  if (
    status === "waiting_validation" ||
    status === "future_meeting" ||
    status === "pending_cp_evaluation" ||
    status === "pending_client_evaluation" ||
    status === "waiting_client_validation" ||
    status === "pending" ||
    status === "scheduled" ||
    status === "pending_followup" ||
    status === "next_step_scheduled" ||
    status === "requested_proposal" ||
    status === "proposal_sent" ||
    status === "proposal_followup" ||
    status === "negotiation"
  ) {
    return "warn";
  }

  if (
    status === "not_valid_cp" ||
    status === "not_valid_client" ||
    status === "final_not_valid" ||
    status === "evaluation_closed_not_valid" ||
    status === "cancelled_meeting" ||
    status === "cancelled" ||
    status === "no_show" ||
    status === "not_completed" ||
    status === "client_lost" ||
    status === "not_commercially_qualified" ||
    status === "no_response"
  ) {
    return "bad";
  }

  return "neutral";
};

export function StatusBadge({ status, label, size = "md" }: StatusBadgeProps) {
  const tone = toneStyles[getTone(status)];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        tone.pill,
        size === "sm" ? "px-2.5 py-1 text-[10.5px]" : "px-3 py-1 text-[11px]"
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone.dot }} />
      {label}
    </span>
  );
}
