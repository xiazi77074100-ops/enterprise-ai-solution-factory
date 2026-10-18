import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useState } from "react";

import { Button } from "./ui";

const SIZES = [25, 50, 100, 200] as const;

/** Cursor paging over the API's opaque cursors: keeps the stack of visited cursors for 「前へ」. */
export function useCursorPagination(resetKey: string) {
  const [state, setState] = useState({ key: resetKey, stack: [] as (string | null)[], limit: 50 });
  // Conditions changed → back to the first page (ui-design §4.2).
  const current = state.key === resetKey ? state : { key: resetKey, stack: [], limit: state.limit };
  const cursor = current.stack.at(-1) ?? null;
  const next = useCallback(
    (nextCursor: string) => setState((s) => ({ ...s, key: resetKey, stack: [...(s.key === resetKey ? s.stack : []), nextCursor] })),
    [resetKey],
  );
  const prev = useCallback(() => setState((s) => ({ ...s, stack: s.stack.slice(0, -1) })), []);
  const setLimit = useCallback((limit: number) => setState({ key: resetKey, stack: [], limit }), [resetKey]);
  return { cursor, limit: current.limit, pageIndex: current.stack.length, next, prev, setLimit };
}

export function Pagination({
  total,
  pageIndex,
  limit,
  rows,
  nextCursor,
  onNext,
  onPrev,
  onLimit,
}: {
  total: number;
  pageIndex: number;
  limit: number;
  rows: number;
  nextCursor: string | null;
  onNext: (cursor: string) => void;
  onPrev: () => void;
  onLimit: (limit: number) => void;
}) {
  const start = total === 0 ? 0 : pageIndex * limit + 1;
  const end = pageIndex * limit + rows;
  const pages = Math.max(1, Math.ceil(total / limit));
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-border px-3 py-2 text-[12px] text-muted-foreground">
      <span className="flex-1 whitespace-nowrap">
        {total === 0 ? "0 件" : `${total.toLocaleString("ja-JP")} 件中 ${start}–${end} 件目を表示`}
      </span>
      <label className="flex items-center gap-1">
        <span>表示件数</span>
        <select
          className="h-7 rounded border border-input bg-card px-1"
          value={limit}
          onChange={(e) => onLimit(Number(e.target.value))}
        >
          {SIZES.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
      {/* prev / position / next wrap together, never leaving one button alone on a line */}
      <span className="flex items-center gap-1">
        <Button variant="ghost" aria-label="前のページ" disabled={pageIndex === 0} onClick={onPrev} icon={<ChevronLeft className="size-4" />} />
        <span className="whitespace-nowrap tabular-nums">
          {pageIndex + 1} / {pages}
        </span>
        <Button
          variant="ghost"
          aria-label="次のページ"
          disabled={!nextCursor}
          onClick={() => nextCursor && onNext(nextCursor)}
          icon={<ChevronRight className="size-4" />}
        />
      </span>
    </div>
  );
}
