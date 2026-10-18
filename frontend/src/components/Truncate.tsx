import { clsx } from "clsx";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

/** ui-design §4.1: cut long text with "…" and show the full text on hover only when it is cut.
 *  The full text stays in the DOM (search, copy, screen readers). */
export function Truncate({
  children,
  text,
  lines = 1,
  className,
}: {
  children: ReactNode;
  text?: string;
  lines?: 1 | 2;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [cut, setCut] = useState(false);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setCut(el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [children]);

  const full = text ?? (typeof children === "string" ? children : undefined);
  return (
    <span
      ref={ref}
      title={cut ? full : undefined}
      className={clsx("block min-w-0", lines === 1 ? "truncate" : "line-clamp-2", className)}
    >
      {children}
    </span>
  );
}
