import { CheckCircle2, FileText, Users } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { api, type Schemas } from "../../api/client";
import { useAuth } from "../../app/auth";
import { useApi } from "../../app/feedback";
import { useLoad } from "../../app/useLoad";
import { Field, useFormCheck } from "../../components/Field";
import { EmptyRow, PageHeader, Panel } from "../../components/layout";
import { ConfirmDialog } from "../../components/Modal";
import { Truncate } from "../../components/Truncate";
import { Badge, Button } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { firstError, maxLength, required } from "../../lib/validation";

const ROLE_LABELS: Record<string, string> = {
  solution_lead: "責任者",
  solution_architect: "設計担当",
  qa_evaluator: "評価担当",
  business_reviewer: "業務確認者",
};

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  const { session } = useAuth();
  const project = useLoad(() => api<Schemas["Project"]>("GET", `/api/v1/projects/${encodeURIComponent(projectId)}`), projectId);
  const members = useLoad(
    () => api<Schemas["ProjectMember"][]>("GET", `/api/v1/projects/${encodeURIComponent(projectId)}/members`),
    projectId,
  );
  const myRoles = members.data?.find((m) => m.user_id === session?.user.id)?.roles ?? [];

  if (project.error) {
    return (
      <div className="p-4">
        <PageHeader title="プロジェクト" breadcrumb={{ label: "プロジェクト一覧", to: "/projects", current: "—" }} />
        <p role="status" className="card mt-3 px-3 py-2 text-[12px] text-danger-ink">
          {project.error.message}
        </p>
      </div>
    );
  }
  const p = project.data;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b border-border bg-background px-4 py-3">
        <PageHeader
          title={p?.name ?? "読み込み中…"}
          titleVisible
          breadcrumb={{ label: "プロジェクト一覧", to: "/projects", current: p?.name ?? "…" }}
        >
          {p && (
            <span className="flex flex-wrap gap-x-4">
              <span>業務区分：{p.business_domain}</span>
              <span>更新：{formatDateTime(p.updated_at)}</span>
            </span>
          )}
        </PageHeader>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
        {p?.description && (
          <Panel title="概要" icon={FileText}>
            <p className="whitespace-pre-wrap text-[13px]">{p.description}</p>
          </Panel>
        )}
        <RequirementsPanel projectId={projectId} myRoles={myRoles} myId={session?.user.id ?? ""} />
        <Panel title="メンバー" icon={Users} meta={members.data ? `${members.data.length} 人` : undefined}>
          <ul className="divide-y divide-border">
            {(members.data ?? []).map((m) => (
              <li key={m.user_id} className="flex items-center gap-2 py-2">
                <Truncate className="max-w-[240px] font-semibold">{m.display_name ?? m.user_id}</Truncate>
                <span className="flex flex-wrap gap-1">
                  {m.roles.map((r) => (
                    <Badge key={r} tone="primary">
                      {ROLE_LABELS[r] ?? r}
                    </Badge>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function RequirementsPanel({ projectId, myRoles, myId }: { projectId: string; myRoles: string[]; myId: string }) {
  const revisions = useLoad(
    () => api<Schemas["RequirementRevision"][]>("GET", `/api/v1/projects/${encodeURIComponent(projectId)}/requirements`),
    projectId,
  );
  const save = useApi();
  const approve = useApi();
  const [content, setContent] = useState("");
  const [confirming, setConfirming] = useState<Schemas["RequirementRevision"] | null>(null);
  const canWrite = myRoles.includes("solution_lead") || myRoles.includes("solution_architect");
  const canApprove = myRoles.includes("solution_lead");
  const form = useFormCheck({ content: firstError(required(content, "要件"), maxLength(content, 20000, "要件")) });

  const submit = async () => {
    const created = await save.run(
      () => api("POST", `/api/v1/projects/${encodeURIComponent(projectId)}/requirements`, { body: { content: content.trim() } }),
      "要件の版を登録しました。",
    );
    if (created) {
      setContent("");
      form.reset();
      revisions.reload();
    }
  };

  const doApprove = async () => {
    if (!confirming) return;
    const done = await approve.run(() => api("POST", `/api/v1/requirements/${encodeURIComponent(confirming.id)}/approve`), "要件を承認しました。");
    if (done) {
      setConfirming(null);
      revisions.reload();
    }
  };

  const rows = revisions.data ?? [];
  return (
    <Panel title="要件の版" icon={FileText} meta={revisions.data ? `${rows.length} 件` : undefined}>
      {canWrite && (
        <div className="mb-4 flex flex-col gap-2">
          <Field label="新しい要件" required hint="登録すると新しい版になります。承認は作成者以外の責任者が行います。" {...form.field("content", content !== "")}>
            <textarea className="field-control" value={content} onChange={(e) => setContent(e.target.value)} />
          </Field>
          <div>
            <Button variant="default" disabled={!form.valid} loading={save.busy} onClick={submit}>
              版を登録
            </Button>
          </div>
        </div>
      )}
      {/* relative: keeps the absolutely positioned sr-only header inside the scroll area */}
      <div className="relative overflow-x-auto">
        <table className="zebra w-full min-w-[560px] text-[13px]">
          <thead className="text-[12px] text-muted-foreground">
            <tr className="border-b border-border text-left">
              <th scope="col" className="px-3 py-2 text-right font-semibold">版</th>
              <th scope="col" className="px-3 py-2 font-semibold">内容</th>
              <th scope="col" className="px-3 py-2 font-semibold">状態</th>
              <th scope="col" className="px-3 py-2 font-semibold">登録日時</th>
              <th scope="col" className="px-3 py-2 font-semibold"><span className="sr-only">操作</span></th>
            </tr>
          </thead>
          <tbody>
            {revisions.data && rows.length === 0 && <EmptyRow colSpan={5}>要件はまだ登録されていません</EmptyRow>}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-border last:border-0">
                <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">第 {r.revision} 版</td>
                <td className="px-3 py-2">
                  <Truncate lines={2} className="max-w-[420px]">{r.content}</Truncate>
                </td>
                <td className="px-3 py-2">
                  {r.approved_at ? <Badge tone="success">承認済み</Badge> : <Badge tone="warning">未承認</Badge>}
                </td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(r.created_at)}</td>
                <td className="whitespace-nowrap px-3 py-2 text-right">
                  {canApprove && !r.approved_at && (
                    <Button icon={<CheckCircle2 className="size-3.5" />} onClick={() => setConfirming(r)}>
                      承認
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ConfirmDialog
        open={confirming !== null}
        onOpenChange={(open) => !open && setConfirming(null)}
        title="要件の承認"
        confirmLabel="承認する"
        busy={approve.busy}
        onConfirm={doApprove}
      >
        <p>第 {confirming?.revision} 版を承認します。承認後は取り消せません。</p>
        {confirming && myId && (
          <p className="mt-2 text-[12px] text-muted-foreground">自分が作成した版は承認できません（サーバで確認します）。</p>
        )}
      </ConfirmDialog>
    </Panel>
  );
}
