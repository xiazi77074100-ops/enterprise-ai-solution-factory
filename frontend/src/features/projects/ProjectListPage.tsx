import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api, type Schemas } from "../../api/client";
import { useLoad } from "../../app/useLoad";
import { EmptyRow, FilterBar, PageHeader } from "../../components/layout";
import { Pagination, useCursorPagination } from "../../components/Pagination";
import { Truncate } from "../../components/Truncate";
import { Button } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { CreateProjectDialog } from "./CreateProjectDialog";

const SORTS = [
  { value: "-updated_at", label: "更新日の新しい順" },
  { value: "updated_at", label: "更新日の古い順" },
  { value: "name", label: "名前の昇順" },
  { value: "-name", label: "名前の降順" },
] as const;

export function ProjectListPage() {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<(typeof SORTS)[number]["value"]>("-updated_at");
  const [creating, setCreating] = useState(false);
  const paging = useCursorPagination(`${q}|${sort}`);
  const { data, error, reload } = useLoad(
    () =>
      api<Schemas["ProjectPage"]>("GET", "/api/v1/projects", {
        query: { q, sort, limit: paging.limit, cursor: paging.cursor },
      }),
    `${q}|${sort}|${paging.limit}|${paging.cursor}`,
  );
  const rows = data?.items ?? [];

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <PageHeader title="プロジェクト一覧">
        <span>参加しているプロジェクトだけを表示します。</span>
      </PageHeader>
      <FilterBar
        search={
          <label className="relative w-full sm:w-64">
            <span className="sr-only">プロジェクト名で検索</span>
            <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" aria-hidden="true" />
            <input
              className="field-control pl-8"
              placeholder="プロジェクト名で検索"
              maxLength={100}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
        }
        actions={
          <Button variant="default" icon={<Plus className="size-4" />} onClick={() => setCreating(true)}>
            新規作成
          </Button>
        }
      >
        <label className="flex items-center gap-1 text-[12px]">
          <span className="text-muted-foreground">並び順</span>
          <select className="field-control w-auto" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
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
          <table className="zebra w-full min-w-[640px] text-[13px]">
            <thead className="sticky top-0 bg-card text-[12px] text-muted-foreground">
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-3 py-2 font-semibold">プロジェクト名</th>
                <th scope="col" className="px-3 py-2 font-semibold">業務区分</th>
                <th scope="col" className="px-3 py-2 font-semibold">更新日時</th>
              </tr>
            </thead>
            <tbody>
              {data && rows.length === 0 && <EmptyRow colSpan={3}>条件に一致するプロジェクトはありません</EmptyRow>}
              {rows.map((p) => (
                <tr key={p.id} className="border-b border-border last:border-0">
                  <td className="px-3 py-2">
                    <Link to={`/projects/${p.id}`} className="block max-w-[320px] font-semibold text-primary-ink hover:underline">
                      <Truncate>{p.name}</Truncate>
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <Truncate className="max-w-[200px]">{p.business_domain}</Truncate>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(p.updated_at)}</td>
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
      <CreateProjectDialog open={creating} onOpenChange={setCreating} onCreated={reload} />
    </div>
  );
}
