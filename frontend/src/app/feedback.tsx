// Shared feedback (ui-design §5.4): a top line while any API call runs, and ActionDialog for results.
import { CheckCircle2, TriangleAlert, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { ApiError } from "../api/client";

type Notice = { kind: "success" | "error"; message: string; traceId?: string | null };

type Feedback = {
  pending: number;
  track: <T>(promise: Promise<T>) => Promise<T>;
  notify: (notice: Notice) => void;
};

const FeedbackContext = createContext<Feedback | null>(null);

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState(0);
  const [notice, setNotice] = useState<Notice | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const track = useCallback(<T,>(promise: Promise<T>) => {
    setPending((n) => n + 1);
    return promise.finally(() => setPending((n) => n - 1));
  }, []);

  const notify = useCallback((next: Notice) => {
    window.clearTimeout(timer.current);
    setNotice(next);
    if (next.kind === "success") timer.current = window.setTimeout(() => setNotice(null), 4000);
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);
  const value = useMemo(() => ({ pending, track, notify }), [pending, track, notify]);

  return (
    <FeedbackContext.Provider value={value}>
      {pending > 0 && <div className="api-line" aria-hidden="true" />}
      {children}
      {notice && (
        <div
          role={notice.kind === "error" ? "alert" : "status"}
          aria-live={notice.kind === "error" ? "assertive" : "polite"}
          className={`card fixed left-1/2 top-16 z-[150] flex w-[min(92vw,440px)] -translate-x-1/2 items-start gap-2 px-4 py-3 ${
            notice.kind === "error" ? "bg-danger-soft text-danger-ink" : "bg-success-soft text-success-ink"
          }`}
        >
          {notice.kind === "error" ? (
            <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          )}
          <p className="flex-1 text-[13px]">
            {notice.message}
            {notice.traceId && <span className="block text-[11px]">trace_id: {notice.traceId}</span>}
          </p>
          <button
            type="button"
            className="grid size-8 place-items-center rounded"
            aria-label="閉じる"
            onClick={() => setNotice(null)}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      )}
    </FeedbackContext.Provider>
  );
}

export function useFeedback(): Feedback {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("FeedbackProvider is missing");
  return ctx;
}

/** Wraps one write operation: busy flag for its button, shared top line, error notice. */
export function useApi() {
  const { track, notify } = useFeedback();
  const [busy, setBusy] = useState(false);
  const run = useCallback(
    async <T,>(fn: () => Promise<T>, success?: string): Promise<T | undefined> => {
      setBusy(true);
      try {
        const result = await track(fn());
        if (success) notify({ kind: "success", message: success });
        return result;
      } catch (err) {
        notify(toNotice(err));
        return undefined;
      } finally {
        setBusy(false);
      }
    },
    [track, notify],
  );
  return { busy, run };
}

export function toNotice(err: unknown): Notice {
  if (err instanceof ApiError) return { kind: "error", message: err.message, traceId: err.traceId };
  return { kind: "error", message: "通信できませんでした。しばらく待ってからお試しください。" };
}
