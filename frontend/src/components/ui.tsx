import { clsx } from "clsx";
import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "default" | "outline" | "ghost" | "danger" | "dangerSolid";

const VARIANTS: Record<Variant, string> = {
  default: "bg-primary text-primary-foreground hover:opacity-90",
  outline: "border border-input bg-card hover:bg-muted",
  ghost: "hover:bg-muted",
  danger: "border border-danger/40 bg-danger-soft text-danger-ink hover:border-danger",
  dangerSolid: "bg-danger text-white hover:opacity-90",
};

export function Button({
  variant = "outline",
  loading = false,
  icon,
  className,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean; icon?: ReactNode }) {
  return (
    <button
      type="button"
      {...props}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={clsx(
        "inline-flex h-8 min-w-8 items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-3 text-[13px] font-semibold",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
    >
      {loading ? <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> : icon}
      {children}
    </button>
  );
}

export type Tone = "neutral" | "primary" | "success" | "warning" | "danger" | "mock";

const TONES: Record<Tone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  primary: "border-primary/30 bg-primary-soft text-primary-ink",
  success: "border-success/30 bg-success-soft text-success-ink",
  warning: "border-warning/40 bg-warning-soft text-warning-ink",
  danger: "border-danger/30 bg-danger-soft text-danger-ink",
  mock: "border-mock/40 bg-mock-soft text-mock-ink",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center whitespace-nowrap rounded border px-1.5 text-[11px] font-semibold leading-5",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Immutable capability/rule pack version, shown as id@version in monospace (ui-design §7). */
export function VersionTag({ id, version }: { id: string; version: string }) {
  return (
    <span className="whitespace-nowrap font-mono text-[11px] text-muted-foreground">
      {id}@{version}
    </span>
  );
}
