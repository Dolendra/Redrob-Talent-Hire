import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="border-b border-border/60 bg-background/60 px-6 py-6 lg:px-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          {eyebrow && (
            <div className="text-[10px] uppercase tracking-[0.22em] font-mono text-primary mb-2">
              {eyebrow}
            </div>
          )}
          <h1 className="font-display text-2xl lg:text-3xl font-semibold tracking-tight">
            {title}
          </h1>
          {description && (
            <p className="mt-2 text-sm text-muted-foreground max-w-2xl">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
