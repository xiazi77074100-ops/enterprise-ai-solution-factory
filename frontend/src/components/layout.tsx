import { clsx } from "clsx";
import type { ComponentType, ReactNode } from "react";
import { Link } from "react-router-dom";

/** ui-design §1: the h1 is for screen readers unless the title is a record name (titleVisible). */
export function PageHeader({
  title,
  titleVisible = false,
  breadcrumb,
  actions,
  children,
}: {
  title: string;
  titleVisible?: boolean;
  breadcrumb?: { label: string; to: string; current: string };
  actions?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-1">
      {breadcrumb && (
        <nav aria-label="パンくず" className="text-[12px] text-muted-foreground">
          <Link to={breadcrumb.to} className="hover:underline">
            {breadcrumb.label}
          </Link>
          <span aria-hidden="true"> › </span>
          <span>{breadcrumb.current}</span>
        </nav>
      )}
      <h1 className={titleVisible ? "page-title" : "sr-only"}>{title}</h1>
      {(children || actions) && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex-1 text-[12px] text-muted-foreground">{children}</div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
    </header>
  );
}

export function Panel({
  title,
  icon: Icon,
  meta,
  actions,
  children,
  className,
}: {
  title: string;
  icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("card", className)} aria-label={title}>
      <div className="panel-head">
        {Icon && <Icon className="size-4 text-muted-foreground" aria-hidden={true} />}
        <h2 className="panel-title">{title}</h2>
        {meta && <span className="text-[12px] text-muted-foreground">{meta}</span>}
        <span className="flex-1" />
        {actions}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

/** Conditions row above a list: filters on the left, actions grouped on the right (ui-design §1). */
export function FilterBar({ search, actions, children }: { search?: ReactNode; actions?: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {search}
      {children}
      <span className="min-w-0 flex-1" />
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyRow({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-10 text-center text-muted-foreground">
        {children}
      </td>
    </tr>
  );
}
