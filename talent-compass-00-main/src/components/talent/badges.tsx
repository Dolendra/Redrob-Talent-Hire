import type { Recommendation } from "@/lib/scoring/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function RecommendationBadge({ value }: { value: Recommendation }) {
  const map = {
    strong_hire: {
      label: "Strong Hire",
      cls: "bg-safe/15 text-safe border-safe/40 shadow-[0_0_16px_-4px_var(--color-safe)]",
    },
    consider: {
      label: "Consider",
      cls: "bg-stretch/15 text-stretch border-stretch/40",
    },
    pass: {
      label: "Pass",
      cls: "bg-muted text-muted-foreground border-border",
    },
  } as const;
  const { label, cls } = map[value];
  return (
    <Badge variant="outline" className={cn("font-mono uppercase tracking-wider text-[10px] px-2 py-1", cls)}>
      {label}
    </Badge>
  );
}

export function QuadrantBadge({ q }: { q: "safe" | "gem" | "stretch" | "pass" }) {
  const map = {
    safe: { label: "Safe", cls: "text-safe border-safe/40" },
    gem: { label: "◆ Gem", cls: "text-gem border-gem/40 bg-gem/10" },
    stretch: { label: "Stretch", cls: "text-stretch border-stretch/40" },
    pass: { label: "Pass", cls: "text-muted-foreground border-border" },
  } as const;
  const { label, cls } = map[q];
  return (
    <Badge variant="outline" className={cn("font-mono text-[10px] uppercase tracking-wider", cls)}>
      {label}
    </Badge>
  );
}
