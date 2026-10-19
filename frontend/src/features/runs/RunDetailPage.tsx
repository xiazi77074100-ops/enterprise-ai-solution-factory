import { ClipboardCheck, Download, ListTree, ScrollText } from "lucide-react";
import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";

import { api, type Schemas } from "../../api/client";
import { useLoad } from "../../app/useLoad";
import { EmptyRow, PageHeader, Panel } from "../../components/layout";
import { Pagination, useCursorPagination } from "../../components/Pagination";
import { Badge, DownloadLink, VersionTag } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { DECISION, EVENT, failureText, ModeBadge, NodeStatusBadge, shortId, StatusBadge } from "./labels";

type TraceEvent = {
  event_id: string;
  event_type: string;
  timestamp: string;
  node_id: string | null;
  status: string;
  actor: { type: "user" | "system"; id: string };
  redacted_metadata: Record<string, string | number | boolean | null>;
};

const LIVE = new Set(["pending", "running"]);
const POLL_MS = 3000;

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const run = useLoad(() => api<Schemas["Run"]>("GET", `/api/v1/runs/${encodeURIComponent(runId)}`), runId);
  const nodes = useLoad(() => api<Schemas["NodeRun"][]>("GET", `/api/v1/runs/${encodeURIComponent(runId)}/nodes`), runId);
  const project = useLoad(
    () => (run.data ? api<Schemas["Project"]>("GET", `/api/v1/projects/${run.data.project_id}`) : Promise.resolve(null)),
    run.data?.project_id ?? "",
  );
  const live = run.data ? LIVE.has(run.data.status) : false;
  const { reload: reloadRun } = run;
  const { reload: reloadNodes } = nodes;

  // Execution monitor (ui-design §5.4): long runs are followed here instead of keeping the user waiting.
  useEffect(() => {
    if (!live) return;
    const timer = window.setInterval(() => {
      reloadRun();
      reloadNodes();
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [live, reloadRun, reloadNodes]);

  if (run.error) {
    return (
      <div className="p-4">
        <PageHeader title="実行" breadcrumb={{ label: "プロジェクト一覧", to: "/projects", current: "—" }} />
        <p role="status" className="card mt-3 px-3 py-2 text-[12px] text-danger-ink">
          {run.error.message}
        </p>
      </div>
    );
  }
  const r = run.data;
  const failure = failureText(r?.failure_code);
  // exportRunResult: only succeeded runs whose exporter node succeeded (the server checks roles and content).
  const exportable =
    r?.status === "succeeded" && (nodes.data ?? []).some((n) => n.capability_id === "result.exporter" && n.status === "succeeded");
  const exportHref = (format: "csv" | "json") => `/api/v1/runs/${encodeURIComponent(runId)}/export?format=${format}`;
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b border-border bg-background px-4 py-3">
        <PageHeader
          title={r ? `実行 ${shortId(r.id)}` : "読み込み中…"}
          titleVisible
          actions={
            exportable && (
              <span className="flex gap-2">
                <DownloadLink href={exportHref("csv")} icon={<Download className="size-3.5" />}>
                  CSV で出力
                </DownloadLink>
                <DownloadLink href={exportHref("json")} icon={<Download className="size-3.5" />}>
                  JSON で出力
                </DownloadLink>
              </span>
            )
          }
          breadcrumb={{
            label: project.data?.name ?? "プロジェクト",
            to: r ? `/projects/${r.project_id}` : "/projects",
            current: r ? `実行 ${shortId(r.id)}` : "…",
          }}
        >
          {r && (
            <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <StatusBadge status={r.status} />
              <ModeBadge mode={r.execution_mode} />
              <span>開始：{formatDateTime(r.started_at)}</span>
              <span>終了：{formatDateTime(r.finished_at)}</span>
              {live && <span role="status">自動で更新しています</span>}
            </span>
          )}
        </PageHeader>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
        {r && failure && (
          <p role="status" className="card bg-danger-soft px-3 py-2 text-[13px] text-danger-ink">
            {failure}（{r.failure_code}）
          </p>
        )}
        {r?.status === "waiting_review" && <ReviewNotice runId={r.id} />}
        <Panel title="処理の流れ" icon={ListTree} meta={nodes.data ? `${nodes.data.length} 件` : undefined}>
          <div className="relative overflow-x-auto">
            <table className="zebra w-full min-w-[720px] text-[13px]">
              <thead className="text-[12px] text-muted-foreground">
                <tr className="border-b border-border text-left">
                  <th scope="col" className="px-3 py-2 font-semibold">処理</th>
                  <th scope="col" className="px-3 py-2 font-semibold">状態</th>
                  <th scope="col" className="px-3 py-2 font-semibold">方式</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">試行</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">時間</th>
                  <th scope="col" className="px-3 py-2 font-semibold">結果</th>
                </tr>
              </thead>
              <tbody>
                {nodes.data && nodes.data.length === 0 && <EmptyRow colSpan={6}>処理はありません</EmptyRow>}
                {(nodes.data ?? []).map((n) => (
                  <tr key={n.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2">
                      <span className="block font-semibold">{n.node_id}</span>
                      <VersionTag id={n.capability_id} version={n.capability_version} />
                    </td>
                    <td className="px-3 py-2">
                      <NodeStatusBadge status={n.status} />
                    </td>
                    <td className="px-3 py-2">
                      <ModeBadge mode={n.execution_mode} />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{n.attempt}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                      {n.duration_ms === null ? "—" : `${n.duration_ms.toLocaleString("ja-JP")} ms`}
                    </td>
                    <td className="px-3 py-2 text-[12px]">
                      {n.error_code ? (
                        <span className="text-danger-ink">{failureText(n.error_code)}</span>
                      ) : n.output_summary ? (
                        <span className="text-muted-foreground">
                          {Object.entries(n.output_summary)
                            .map(([k, v]) => `${k}: ${typeof v === "number" ? `${v} 件` : String(v)}`)
                            .join("、")}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        {r && <TracePanel runId={r.id} version={`${r.status}|${nodes.data?.map((n) => n.status).join(",")}`} />}
      </div>
    </div>
  );
}

function ReviewNotice({ runId }: { runId: string }) {
  // Only leads and reviewers can list review tasks; others just see the state.
  const tasks = useLoad(
    () =>
      api<Schemas["ReviewTaskPage"]>("GET", "/api/v1/reviews", {
        query: { status: "pending", assigned_to_me: "false", limit: 200 },
      }).catch(() => null),
    runId,
  );
  const task = tasks.data?.items.find((t) => t.run_id === runId);
  return (
    <div role="status" className="card flex flex-wrap items-center gap-2 bg-warning-soft px-3 py-2 text-[13px] text-warning-ink">
      <ClipboardCheck className="size-4" aria-hidden="true" />
      <span className="flex-1">業務確認者の確認を待っています。確認が終わるまで、この実行は完了しません。</span>
      {task && (
        <Link className="font-semibold underline" to={`/runs/${runId}/reviews/${task.id}`}>
          確認を開く
        </Link>
      )}
    </div>
  );
}

function summary(e: TraceEvent): string {
  const m = e.redacted_metadata;
  if (typeof m.decision === "string") {
    const n = typeof m.correction_count === "number" ? m.correction_count : 0;
    return `${DECISION[m.decision] ?? m.decision}${n > 0 ? `（修正 ${n} 件）` : ""}`;
  }
  if (typeof m.error_code === "string") return `${failureText(m.error_code)}${m.will_retry ? "（再試行）" : ""}`;
  if (typeof m.failure_code === "string") return failureText(m.failure_code) ?? "";
  if (typeof m.item_count === "number") return `確認項目 ${m.item_count} 件`;
  return "";
}

function TracePanel({ runId, version }: { runId: string; version: string }) {
  const paging = useCursorPagination(runId);
  const trace = useLoad(
    () =>
      api<{ items: TraceEvent[]; page: Schemas["PageInfo"] }>("GET", `/api/v1/runs/${encodeURIComponent(runId)}/trace`, {
        query: { limit: paging.limit, cursor: paging.cursor },
      }),
    `${runId}|${paging.limit}|${paging.cursor}|${version}`,
  );
  const rows = trace.data?.items ?? [];
  return (
    <Panel title="記録（トレース）" icon={ScrollText} meta={trace.data ? `${trace.data.page.total} 件` : undefined}>
      <p className="mb-3 text-[12px] text-muted-foreground">
        記録には値そのものを残さず、ハッシュと件数だけを残します。記録は追記だけで、変更・削除できません。
      </p>
      <div className="card overflow-hidden">
        <div className="relative overflow-x-auto">
          <table className="zebra w-full min-w-[640px] text-[13px]">
            <thead className="text-[12px] text-muted-foreground">
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-3 py-2 font-semibold">日時</th>
                <th scope="col" className="px-3 py-2 font-semibold">出来事</th>
                <th scope="col" className="px-3 py-2 font-semibold">処理</th>
                <th scope="col" className="px-3 py-2 font-semibold">実施者</th>
                <th scope="col" className="px-3 py-2 font-semibold">内容</th>
              </tr>
            </thead>
            <tbody>
              {trace.data && rows.length === 0 && <EmptyRow colSpan={5}>記録はありません</EmptyRow>}
              {rows.map((e) => (
                <tr key={e.event_id} className="border-b border-border last:border-0">
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(e.timestamp)}</td>
                  <td className="whitespace-nowrap px-3 py-2">{EVENT[e.event_type] ?? e.event_type}</td>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-[12px]">{e.node_id ?? "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {e.actor.type === "user" ? <Badge tone="primary">利用者</Badge> : <Badge>システム</Badge>}
                  </td>
                  <td className="px-3 py-2 text-[12px]">{summary(e) || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {trace.data && (
          <Pagination
            total={trace.data.page.total}
            pageIndex={paging.pageIndex}
            limit={paging.limit}
            rows={rows.length}
            nextCursor={trace.data.page.next_cursor}
            onNext={paging.next}
            onPrev={paging.prev}
            onLimit={paging.setLimit}
          />
        )}
      </div>
    </Panel>
  );
}
