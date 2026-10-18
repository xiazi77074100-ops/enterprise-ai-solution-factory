import { History } from "lucide-react";
import { Link } from "react-router-dom";

import { api, type Schemas } from "../../api/client";
import { useLoad } from "../../app/useLoad";
import { EmptyRow, Panel } from "../../components/layout";
import { Pagination, useCursorPagination } from "../../components/Pagination";
import { formatDateTime } from "../../lib/format";
import { ModeBadge, shortId, StatusBadge } from "./labels";

export function RunsPanel({ projectId }: { projectId: string }) {
  const paging = useCursorPagination(projectId);
  const list = useLoad(
    () =>
      api<Schemas["RunPage"]>("GET", "/api/v1/runs", {
        query: { project_id: projectId, limit: paging.limit, cursor: paging.cursor },
      }),
    `${projectId}|${paging.limit}|${paging.cursor}`,
  );
  const rows = list.data?.items ?? [];
  return (
    <Panel title="実行" icon={History} meta={list.data ? `${list.data.page.total} 件` : undefined}>
      <div className="card overflow-hidden">
        <div className="relative overflow-x-auto">
          <table className="zebra w-full min-w-[600px] text-[13px]">
            <thead className="text-[12px] text-muted-foreground">
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-3 py-2 font-semibold">実行番号</th>
                <th scope="col" className="px-3 py-2 font-semibold">状態</th>
                <th scope="col" className="px-3 py-2 font-semibold">方式</th>
                <th scope="col" className="px-3 py-2 font-semibold">開始</th>
                <th scope="col" className="px-3 py-2 font-semibold">終了</th>
              </tr>
            </thead>
            <tbody>
              {list.data && rows.length === 0 && <EmptyRow colSpan={5}>実行はまだありません</EmptyRow>}
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-border last:border-0">
                  <td className="whitespace-nowrap px-3 py-2">
                    <Link to={`/runs/${r.id}`} className="font-mono font-semibold text-primary-ink hover:underline">
                      {shortId(r.id)}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-3 py-2">
                    <ModeBadge mode={r.execution_mode} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(r.started_at)}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(r.finished_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {list.data && (
          <Pagination
            total={list.data.page.total}
            pageIndex={paging.pageIndex}
            limit={paging.limit}
            rows={rows.length}
            nextCursor={list.data.page.next_cursor}
            onNext={paging.next}
            onPrev={paging.prev}
            onLimit={paging.setLimit}
          />
        )}
      </div>
    </Panel>
  );
}
