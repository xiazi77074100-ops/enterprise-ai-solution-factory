import { useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError, type Schemas } from "../../api/client";
import { useLoad } from "../../app/useLoad";
import { EmptyRow, FilterBar, PageHeader } from "../../components/layout";
import { Pagination, useCursorPagination } from "../../components/Pagination";
import { Badge } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { DECISION, shortId } from "../runs/labels";

const STATUSES = [
  { value: "pending", label: "確認待ち" },
  { value: "completed", label: "決定済み" },
] as const;

export function ReviewListPage() {
  const [status, setStatus] = useState<(typeof STATUSES)[number]["value"]>("pending");
  const paging = useCursorPagination(status);
  const { data, error } = useLoad(
    () =>
      api<Schemas["ReviewTaskPage"]>("GET", "/api/v1/reviews", {
        query: { status, assigned_to_me: "true", limit: paging.limit, cursor: paging.cursor },
      }),
    `${status}|${paging.limit}|${paging.cursor}`,
  );
  const rows = data?.items ?? [];
  const noRole = error instanceof ApiError && error.status === 403;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <PageHeader title="確認タスク">
        <span>自分に割り当てられた確認です。</span>
      </PageHeader>
      <FilterBar>
        <label className="flex items-center gap-1 text-[12px]">
          <span className="text-muted-foreground">状態</span>
          <select className="field-control w-auto" value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </FilterBar>
      {error && (
        <p role="status" className="card px-3 py-2 text-[12px] text-danger-ink">
          {noRole ? "確認タスクは、責任者か業務確認者のロールを持つ人だけが使えます。" : error.message}
        </p>
      )}
      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="relative min-h-0 flex-1 overflow-auto">
          <table className="zebra w-full min-w-[600px] text-[13px]">
            <thead className="sticky top-0 bg-card text-[12px] text-muted-foreground">
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-3 py-2 font-semibold">実行番号</th>
                <th scope="col" className="px-3 py-2 font-semibold">処理</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">項目数</th>
                <th scope="col" className="px-3 py-2 font-semibold">決定</th>
                <th scope="col" className="px-3 py-2 font-semibold">決定日時</th>
              </tr>
            </thead>
            <tbody>
              {data && rows.length === 0 && <EmptyRow colSpan={5}>該当する確認はありません</EmptyRow>}
              {rows.map((t) => (
                <tr key={t.id} className="border-b border-border last:border-0">
                  <td className="whitespace-nowrap px-3 py-2">
                    <Link to={`/runs/${t.run_id}/reviews/${t.id}`} className="font-mono font-semibold text-primary-ink hover:underline">
                      {shortId(t.run_id)}
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-[12px]">{t.node_id}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{t.items.length}</td>
                  <td className="px-3 py-2">
                    {t.decision ? <Badge tone={t.decision === "rejected" ? "danger" : "success"}>{DECISION[t.decision]}</Badge> : <Badge tone="warning">確認待ち</Badge>}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(t.decided_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && (
          <Pagination
            total={data.page.total}
            pageIndex={paging.pageIndex}
            limit={paging.limit}
            rows={rows.length}
            nextCursor={data.page.next_cursor}
            onNext={paging.next}
            onPrev={paging.prev}
            onLimit={paging.setLimit}
          />
        )}
      </div>
    </div>
  );
}
