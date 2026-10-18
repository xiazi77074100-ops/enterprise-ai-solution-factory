import { cloneElement, isValidElement, useCallback, useId, useMemo, useState, type ReactElement } from "react";

import type { Check } from "../lib/validation";

/** ui-design §5.1: errors are computed on every render (not stored). Fields with a value show errors at once;
 *  empty required fields only after the user leaves them. `valid` drives disabled={!form.valid}. */
export function useFormCheck<K extends string>(errors: Record<K, Check>, serverErrors: Partial<Record<K, string>> = {}) {
  const [touched, setTouched] = useState<Partial<Record<K, boolean>>>({});
  const merged = useMemo(() => {
    const out = { ...errors };
    for (const key of Object.keys(serverErrors) as K[]) out[key] = out[key] ?? serverErrors[key] ?? null;
    return out;
  }, [errors, serverErrors]);
  const valid = Object.values<Check>(merged).every((e) => e === null);
  const field = useCallback(
    (key: K, hasValue: boolean) => ({
      error: touched[key] || hasValue ? merged[key] : null,
      onBlur: () => setTouched((t) => ({ ...t, [key]: true })),
    }),
    [merged, touched],
  );
  const reset = useCallback(() => setTouched({}), []);
  const firstProblem = Object.values<Check>(merged).find((e) => e !== null) ?? null;
  return { valid, field, reset, firstProblem };
}

type ControlProps = {
  id?: string;
  "aria-invalid"?: boolean;
  "aria-required"?: boolean;
  "aria-describedby"?: string;
  onBlur?: () => void;
};

export function Field({
  label,
  required = false,
  error,
  hint,
  onBlur,
  children,
}: {
  label: string;
  required?: boolean;
  error?: Check;
  hint?: string;
  onBlur?: () => void;
  children: ReactElement<ControlProps>;
}) {
  const id = useId();
  const messageId = `${id}-message`;
  const control = isValidElement(children)
    ? cloneElement(children, {
        id,
        "aria-invalid": Boolean(error),
        "aria-required": required || undefined,
        "aria-describedby": error || hint ? messageId : undefined,
        onBlur,
      })
    : children;
  // Floating label (sales-assistant style, D-026): the label sits on the top-left edge of the box.
  return (
    <div className="flex flex-col">
      <div className="floating-field">
        <label htmlFor={id} className="field-label">
          {label}
          {required && (
            <span className="ml-0.5 text-danger-ink" aria-hidden="true">
              *
            </span>
          )}
        </label>
        {control}
      </div>
      {error ? (
        <p id={messageId} role="alert" className="field-message" data-error="true">
          {error}
        </p>
      ) : (
        hint && (
          <p id={messageId} className="field-message">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

/** Footer note: why the primary button is disabled. */
export function FormStatus({ problem }: { problem: Check }) {
  return problem ? <span className="text-[12px] text-muted-foreground">{problem}</span> : null;
}
