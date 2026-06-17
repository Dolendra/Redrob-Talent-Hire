import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface KpiProps {
  label: string;
  value: ReactNode;
  delta?: string;
  hint?: string;
  accent?: "primary" | "gem" | "safe" | "stretch";
  icon?: ReactNode;
}

const accentBar: Record<NonNullable<KpiProps["accent"]>, string> = {
  primary: "bg-primary shadow-[0_0_18px_var(--color-primary)]",
  gem: "bg-gem shadow-[0_0_18px_var(--color-gem)]",
  safe: "bg-safe shadow-[0_0_18px_var(--color-safe)]",
  stretch: "bg-stretch shadow-[0_0_18px_var(--color-stretch)]",
};

export function KpiCard({ label, value, delta, hint, accent = "primary", icon }: KpiProps) {
  return (
    <div className="surface-card rounded-lg p-4 relative overflow-hidden group">
      <div className={cn("absolute left-0 top-0 h-full w-[2px]", accentBar[accent])} />
      <div className="flex items-start justify-between gap-3">
        <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-mono">
          {label}
        </div>
        {icon && <div className="text-muted-foreground opacity-70 group-hover:opacity-100 transition">{icon}</div>}
      </div>
      <div className="mt-2 font-display text-3xl font-semibold tabular-nums">
        {value}
      </div>
      <div className="mt-1 flex items-center gap-2 text-xs">
        {delta && <span className="text-safe font-mono">{delta}</span>}
        {hint && <span className="text-muted-foreground">{hint}</span>}
      </div>
    </div>
  );
}
