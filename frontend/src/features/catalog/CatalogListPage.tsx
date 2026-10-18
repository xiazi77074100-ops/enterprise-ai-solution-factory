import { Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api, type Schemas } from "../../api/client";
import { useLoad } from "../../app/useLoad";
import { EmptyRow, FilterBar, PageHeader } from "../../components/layout";
import { Pagination, useCursorPagination } from "../../components/Pagination";
import { Truncate } from "../../components/Truncate";
import { Badge, VersionTag } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { KIND_LABELS } from "./labels";

type Kind = "" | "local" | "rest" | "mcp_tool" | "llm";

export function CatalogListPage() {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<Kind>("");
  const paging = useCursorPagination(`${q}|${kind}`);
  const { data, error } = useLoad(
    () =>
      api<Schemas["CapabilityVersionPage"]>("GET", "/api/v1/capabilities", {
        query: { q, kind: kind || undefined, limit: paging.limit, cursor: paging.cursor },
      }),
    `${q}|${kind}|${paging.limit}|${paging.cursor}`,
  );
  const rows = data?.items ?? [];

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <PageHeader title="能力カタログ">
        <span>登録済みの版は変更できません。変更は新しい版として登録します。</span>
      </PageHeader>
      <FilterBar
        search={
          <label className="relative w-full sm:w-64">
            <span className="sr-only">名前・ID で検索</span>
            <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" aria-hidden="true" />
            <input className="field-control pl-8" placeholder="名前・ID で検索" maxLength={100} value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
        }
      >
        {/* The v1 contract filters by one kind at a time, so this is a single choice (see G1a report). */}
        <label className="flex items-center gap-1 text-[12px]">
          <span className="text-muted-foreground">接続方式</span>
          <select className="field-control w-auto" value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
            <option value="">すべて</option>
            {Object.entries(KIND_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </FilterBar>
      {error && (
        <p role="status" className="card px-3 py-2 text-[12px] text-danger-ink">
          {error.message}
        </p>
      )}
      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="min-h-0 flex-1 overflow-auto">
          <table className="zebra w-full min-w-[720px] text-[13px]">
            <thead className="sticky top-0 bg-card text-[12px] text-muted-foreground">
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-3 py-2 font-semibold">能力 / 版</th>
                <th scope="col" className="px-3 py-2 font-semibold">接続方式</th>
                <th scope="col" className="px-3 py-2 font-semibold">説明</th>
                <th scope="col" className="px-3 py-2 font-semibold">登録日時</th>
              </tr>
            </thead>
            <tbody>
              {data && rows.length === 0 && <EmptyRow colSpan={4}>条件に一致する能力はありません</EmptyRow>}
              {rows.map((c) => (
                <tr key={c.id} className="border-b border-border last:border-0">
                  <td className="px-3 py-2">
                    <Link
                      to={`/catalog/${encodeURIComponent(c.capability_id)}/${encodeURIComponent(c.version)}`}
                      className="block max-w-[260px] font-semibold text-primary-ink hover:underline"
                    >
                      <Truncate>{c.name}</Truncate>
                    </Link>
                    <VersionTag id={c.capability_id} version={c.version} />
                  </td>
                  <td className="px-3 py-2">
                    <Badge tone="primary">{KIND_LABELS[c.kind] ?? c.kind}</Badge>
                  </td>
                  <td className="px-3 py-2">
                    <Truncate lines={2} className="max-w-[360px]">
                      {String(c.contract.description ?? "")}
                    </Truncate>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(c.registered_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination
          total={data?.page.total ?? 0}
          pageIndex={paging.pageIndex}
          limit={paging.limit}
          rows={rows.length}
          nextCursor={data?.page.next_cursor ?? null}
          onNext={paging.next}
          onPrev={paging.prev}
          onLimit={paging.setLimit}
        />
      </div>
    </div>
  );
}
