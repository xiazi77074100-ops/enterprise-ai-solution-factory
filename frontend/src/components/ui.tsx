import { clsx } from "clsx";
import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "default" | "outline" | "ghost" | "danger" | "dangerSolid";

// Button styles follow the sales-assistant UI (D-026): gradient primary, quiet outline/ghost, red only for danger.
const VARIANTS: Record<Variant, string> = {
  default:
    "border-transparent bg-primary bg-[image:var(--brand-gradient-deep)] text-primary-foreground hover:brightness-110 hover:shadow-sm",
  outline: "border-input bg-card text-foreground shadow-sm hover:border-primary/45 hover:bg-primary/5 hover:text-primary-ink",
  ghost: "border-transparent text-foreground hover:bg-accent",
  danger: "border-danger/45 bg-danger/10 text-danger-ink hover:border-danger/70 hover:bg-danger/15",
  dangerSolid: "border-danger-fill bg-danger-fill text-white hover:brightness-110",
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
      className={buttonClass(variant, className)}
    >
      {loading ? <Loader2 className="size-3.5 animate-spin" aria-hidden="true" /> : icon}
      {children}
    </button>
  );
}

function buttonClass(variant: Variant, className?: string): string {
  return clsx(
    "inline-flex h-8 min-w-8 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border px-3 text-[13px] font-semibold",
    "transition-[color,background-color,border-color,box-shadow,transform] duration-150 active:scale-[0.98]",
    "disabled:pointer-events-none disabled:opacity-45 disabled:shadow-none",
    VARIANTS[variant],
    className,
  );
}

/** A same-origin file download that looks like a button (the server sends Content-Disposition: attachment). */
export function DownloadLink({ href, icon, children }: { href: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <a href={href} download className={buttonClass("outline")}>
      {icon}
      {children}
    </a>
  );
}

export type Tone = "neutral" | "primary" | "success" | "warning" | "danger" | "mock";

const TONES: Record<Tone, string> = {
  neutral: "bg-muted text-muted-foreground",
  primary: "bg-primary/12 text-primary-ink",
  success: "bg-success/15 text-success-ink",
  warning: "bg-warning/20 text-warning-ink",
  danger: "bg-danger/12 text-danger-ink",
  mock: "bg-mock-soft text-mock-ink ring-1 ring-inset ring-mock/40",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center whitespace-nowrap rounded px-1.5 text-[11px] font-semibold leading-5",
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
