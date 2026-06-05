import { cn } from "@/lib/utils";
import type {
  CPValidation,
  ClientValidation,
  FinalValidation,
  CommercialStatus,
  MeetingStatus,
} from "@/lib/types";

type StatusType = CPValidation | ClientValidation | FinalValidation | CommercialStatus | MeetingStatus;

interface StatusBadgeProps {
  status: StatusType;
  label: string;
  size?: "sm" | "md";
}

const getStatusColor = (status: StatusType): string => {
  // Green statuses
  if (
    status === "valid_cp" ||
    status === "valid_client" ||
    status === "final_valid" ||
    status === "completed" ||
    status === "client_won"
  ) {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }

  // Yellow/warning statuses
  if (
    status === "waiting_validation" ||
    status === "waiting_client_validation" ||
    status === "pending" ||
    status === "scheduled" ||
    status === "requires_review" ||
    status === "pending_followup" ||
    status === "next_step_scheduled" ||
    status === "requested_proposal" ||
    status === "proposal_sent" ||
    status === "proposal_followup" ||
    status === "negotiation"
  ) {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }

  // Red/danger statuses
  if (
    status === "not_valid_cp" ||
    status === "not_valid_client" ||
    status === "final_not_valid" ||
    status === "cancelled" ||
    status === "no_show" ||
    status === "not_completed" ||
    status === "client_lost" ||
    status === "not_commercially_qualified" ||
    status === "no_response"
  ) {
    return "bg-rose-100 text-rose-700 border-rose-200";
  }

  // Orange/dispute statuses
  if (status === "in_dispute") {
    return "bg-orange-100 text-orange-700 border-orange-200";
  }

  // Purple/special statuses
  if (status === "rescheduled" || status === "excluded_by_agreement") {
    return "bg-violet-100 text-violet-700 border-violet-200";
  }

  return "bg-muted text-muted-foreground border-border";
};

export function StatusBadge({ status, label, size = "md" }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border font-medium",
        getStatusColor(status),
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"
      )}
    >
      {label}
    </span>
  );
}

