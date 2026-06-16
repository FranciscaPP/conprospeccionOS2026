import { ReactNode } from "react";

interface KPICardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  trend?: string;
  variant?: "default" | "success" | "warning" | "danger" | "primary";
  active?: boolean;
  onClick?: () => void;
}

const chipStyles = {
  default: "bg-[#efefec] text-[#444]",
  success: "bg-[var(--ok-bg)] text-[var(--ok)]",
  warning: "bg-[var(--warn-bg)] text-[var(--warn)]",
  danger: "bg-[var(--bad-bg)] text-[var(--bad)]",
  primary: "bg-[#fff7cc] text-[#8a6d00]",
};

export function KPICard({ title, value, icon, trend, variant = "default", active = false, onClick }: KPICardProps) {
  const className = `rounded-xl border border-[var(--line)] bg-white p-3 text-left shadow-card transition-shadow ${
    onClick ? "cursor-pointer hover:shadow-[var(--shadow-card-hover)]" : ""
  } ${active ? "ring-2 ring-[var(--carbon)] ring-offset-2" : ""}`;

  const content = (
    <div className="flex items-start justify-between">
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-wide text-[var(--ink-3)] leading-tight">{title}</div>
        <div className="font-display tnum text-[27px] font-semibold leading-none mt-2 text-[var(--ink)]">{value}</div>
        {trend && <div className="mt-1 text-xs text-[var(--ink-3)]">{trend}</div>}
      </div>
      {icon && (
        <div className={`grid h-[30px] w-[30px] place-items-center rounded-lg text-[15px] ${chipStyles[variant]}`}>
          {icon}
        </div>
      )}
    </div>
  );

  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick}>
        {content}
      </button>
    );
  }

  return <div className={className}>{content}</div>;
}
