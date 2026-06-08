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

const variantStyles = {
  default: "bg-card border-border",
  success: "bg-emerald-50 border-emerald-200",
  warning: "bg-amber-50 border-amber-200",
  danger: "bg-rose-50 border-rose-200",
  primary: "bg-violet-50 border-violet-200",
};

const iconVariantStyles = {
  default: "bg-muted text-muted-foreground",
  success: "bg-emerald-100 text-emerald-600",
  warning: "bg-amber-100 text-amber-600",
  danger: "bg-rose-100 text-rose-600",
  primary: "bg-violet-100 text-violet-600",
};

export function KPICard({ title, value, icon, trend, variant = "default", active = false, onClick }: KPICardProps) {
  const className = `rounded-xl border p-4 text-left transition ${
    variantStyles[variant]
  } ${onClick ? "cursor-pointer hover:-translate-y-0.5 hover:shadow-md" : ""} ${
    active ? "ring-2 ring-violet-500 ring-offset-2" : ""
  }`;
  const content = (
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{title}</p>
        <p className="mt-1 text-2xl font-bold text-foreground">{value}</p>
        {trend && <p className="mt-1 text-xs text-muted-foreground">{trend}</p>}
      </div>
      {icon && (
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${iconVariantStyles[variant]}`}>
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

  return (
    <div className={className}>
      {content}
    </div>
  );
}

