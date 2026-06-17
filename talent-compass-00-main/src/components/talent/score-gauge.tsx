import { cn } from "@/lib/utils";

interface ScoreGaugeProps {
  value: number; // 0..100
  label: string;
  sublabel?: string;
  variant?: "primary" | "gem" | "safe" | "stretch" | "pass";
  size?: "md" | "lg";
}

const variantStroke: Record<NonNullable<ScoreGaugeProps["variant"]>, string> = {
  primary: "stroke-primary",
  gem: "stroke-gem",
  safe: "stroke-safe",
  stretch: "stroke-stretch",
  pass: "stroke-pass",
};
const variantGlow: Record<NonNullable<ScoreGaugeProps["variant"]>, string> = {
  primary: "drop-shadow-[0_0_12px_var(--color-primary)]",
  gem: "drop-shadow-[0_0_14px_var(--color-gem)]",
  safe: "drop-shadow-[0_0_12px_var(--color-safe)]",
  stretch: "drop-shadow-[0_0_12px_var(--color-stretch)]",
  pass: "",
};

export function ScoreGauge({
  value,
  label,
  sublabel,
  variant = "primary",
  size = "md",
}: ScoreGaugeProps) {
  const dim = size === "lg" ? 180 : 140;
  const stroke = size === "lg" ? 12 : 10;
  const r = (dim - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const offset = c - (pct / 100) * c;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} className={cn("-rotate-90", variantGlow[variant])}>
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            strokeWidth={stroke}
            className="stroke-muted/40 fill-none"
          />
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
            className={cn("fill-none transition-all duration-1000 ease-out", variantStroke[variant])}
            style={{ transitionDelay: "120ms" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="font-display text-3xl font-semibold tabular-nums">{Math.round(value)}</div>
          <div className="text-[10px] uppercase tracking-[0.18em] font-mono text-muted-foreground">
            / 100
          </div>
        </div>
      </div>
      <div className="mt-2 text-sm font-medium">{label}</div>
      {sublabel && <div className="text-xs text-muted-foreground mt-0.5">{sublabel}</div>}
    </div>
  );
}
