import { CheckCircle2, PencilLine, Undo2 } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { api, newIdempotencyKey, type Schemas } from "../../api/client";
import { useAuth } from "../../app/auth";
import { useApi } from "../../app/feedback";
import { useLoad } from "../../app/useLoad";
import { Field, useFormCheck } from "../../components/Field";
import { PageHeader, Panel } from "../../components/layout";
import { ConfirmDialog } from "../../components/Modal";
import { Truncate } from "../../components/Truncate";
import { Badge, Button } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { maxLength, type Check } from "../../lib/validation";
import { DECISION, RESULT, SEVERITY, shortId } from "../runs/labels";

type Item = Schemas["ReviewItem"];
type Decision = Schemas["ReviewDecision"]["decision"];
type Scalar = string | number | boolean | null;

const ORIGIN: Record<Item["origin"], { label: string; tone: "mock" | "neutral" | "primary" }> = {
  ai_draft: { label: "AI 下書き", tone: "primary" },
  parser: { label: "抽出", tone: "neutral" },
  rule: { label: "ルール", tone: "neutral" },
};

function show(value: unknown): string {
  if (value === null || value === undefined) return "（値なし）";
  if (typeof value === "boolean") return value ? "はい" : "いいえ";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

/** Text an input starts with (untouched input = no correction). */
function initial(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** The edited text as the field's original type; undefined when it cannot be converted. */
function convert(original: unknown, text: string): Scalar | undefined {
  if (typeof original === "number") return /^-?\d+(\.\d+)?$/.test(text.trim()) ? Number(text) : undefined;
  if (typeof original === "boolean") return text === "true" ? true : text === "false" ? false : undefined;
  return text;
}

export function ReviewPage() {
  const { runId = "", reviewId = "" } = useParams();
  const { session } = useAuth();
  const task = useLoad(
    () =>
      api<Schemas["ReviewTask"]>("GET", `/api/v1/runs/${encodeURIComponent(runId)}/reviews/${encodeURIComponent(reviewId)}`),
    `${runId}|${reviewId}`,
  );
  const decide = useApi();
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [comment, setComment] = useState("");
  const [confirming, setConfirming] = useState<Decision | null>(null);
  const [key] = useState(newIdempotencyKey);

  const t = task.data;
  const fields = (t?.items ?? []).filter((i) => i.path.startsWith("/fields/"));
  const findings = (t?.items ?? []).filter((i) => i.origin === "rule");
  const editable = t?.status === "pending" && t.assigned_to === session?.user.id;

  const corrections = fields.flatMap((item) => {
    const text = edits[item.path];
    if (text === undefined || text === initial(item.proposed_value)) return [];
    const value = convert(item.proposed_value, text);
    return [{ path: item.path, corrected_value: value, valid: value !== undefined }];
  });
  const fieldErrors: Record<string, Check> = Object.fromEntries(
    corrections.map((c) => [c.path, c.valid ? null : "元の値と同じ形式で入力してください（数値・はい／いいえ）。"]),
  );
  const form = useFormCheck<string>({ ...fieldErrors, comment: maxLength(comment, 2000, "コメント") });
  const allValid = form.valid;
  const canApprove = editable && allValid && corrections.length === 0;
  const canCorrect = editable && allValid && corrections.length > 0;
  const canReject = editable && allValid && comment.trim() !== "";

  const submit = async () => {
    if (!confirming) return;
    const body: Schemas["ReviewDecision"] = { decision: confirming };
    if (confirming === "approved_with_corrections") {
      body.corrections = corrections.map(({ path, corrected_value }) => ({ path, corrected_value: corrected_value ?? null }));
    }
    if (comment.trim()) body.comment = comment.trim();
    const done = await decide.run(
      () =>
        api("POST", `/api/v1/runs/${encodeURIComponent(runId)}/reviews/${encodeURIComponent(reviewId)}/decision`, {
          body,
          headers: { "Idempotency-Key": key },
        }),
      `「${DECISION[confirming]}」を記録しました。`,
    );
    if (done) {
      setConfirming(null);
      task.reload();
    }
  };

  if (task.error) {
    return (
      <div className="p-4">
        <PageHeader title="確認" breadcrumb={{ label: "確認タスク", to: "/reviews", current: "—" }} />
        <p role="status" className="card mt-3 px-3 py-2 text-[12px] text-danger-ink">
          {task.error.message}
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b border-border bg-background px-4 py-3">
        <PageHeader
          title={`実行 ${shortId(runId)} の確認`}
          titleVisible
          breadcrumb={{ label: "確認タスク", to: "/reviews", current: `実行 ${shortId(runId)}` }}
          actions={
            editable && (
              <>
                <Button variant="danger" icon={<Undo2 className="size-4" />} disabled={!canReject} onClick={() => setConfirming("rejected")}>
                  却下
                </Button>
                <Button icon={<PencilLine className="size-4" />} disabled={!canCorrect} onClick={() => setConfirming("approved_with_corrections")}>
                  修正して承認
                </Button>
                <Button variant="default" icon={<CheckCircle2 className="size-4" />} disabled={!canApprove} onClick={() => setConfirming("approved")}>
                  承認
                </Button>
              </>
            )
          }
        >
          {t && (
            <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
              {t.decision ? (
                <Badge tone={t.decision === "rejected" ? "danger" : "success"}>{DECISION[t.decision]}</Badge>
              ) : (
                <Badge tone="warning">確認待ち</Badge>
              )}
              {t.decided_at && <span>決定：{formatDateTime(t.decided_at)}</span>}
              {!editable && t.status === "pending" && <span>この確認は別の確認者に割り当てられています。</span>}
            </span>
          )}
        </PageHeader>
        {editable && (
          <p className="mt-1 text-[12px] text-muted-foreground">
            {corrections.length > 0
              ? `修正 ${corrections.length} 件。修正して承認するか、修正を戻してください。`
              : "値を直すと「修正して承認」、却下はコメントを書くと押せます。"}
          </p>
        )}
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
        <Panel title="確認する項目" meta={`${fields.length} 件`}>
          <ul className="divide-y divide-border">
            {fields.map((item) => {
              const correction = corrections.find((c) => c.path === item.path);
              return (
                <li key={item.path} className="grid gap-2 py-3 md:grid-cols-[180px_1fr_1fr]">
                  <div>
                    <span className="block font-semibold">{item.label}</span>
                    <Badge tone={ORIGIN[item.origin].tone}>{ORIGIN[item.origin].label}</Badge>
                  </div>
                  <div className="min-w-0">
                    <span className="text-[12px] text-muted-foreground">確認前の値</span>
                    <Truncate lines={2} className={correction ? "line-through" : undefined}>
                      {show(item.proposed_value)}
                    </Truncate>
                    <Evidence item={item} />
                  </div>
                  <div className="min-w-0">
                    {editable ? (
                      <Field label="確認後の値" {...form.field(item.path, Boolean(correction))}>
                        {typeof item.proposed_value === "boolean" ? (
                          <select
                            className="field-control"
                            value={edits[item.path] ?? initial(item.proposed_value)}
                            onChange={(e) => setEdits((v) => ({ ...v, [item.path]: e.target.value }))}
                          >
                            <option value="true">はい</option>
                            <option value="false">いいえ</option>
                          </select>
                        ) : (
                          <input
                            className="field-control"
                            value={edits[item.path] ?? initial(item.proposed_value)}
                            onChange={(e) => setEdits((v) => ({ ...v, [item.path]: e.target.value }))}
                          />
                        )}
                      </Field>
                    ) : (
                      <span className="text-[12px] text-muted-foreground">決定後の値は実行の結果に記録されています。</span>
                    )}
                    {correction && (
                      <span className="mt-1 block text-[12px] text-warning-ink">
                        修正：{show(item.proposed_value)} → {show(correction.corrected_value)}
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </Panel>
        <Panel title="ルールの判定" meta={`${findings.length} 件`}>
          <p className="mb-2 text-[12px] text-muted-foreground">判定は参考情報です。法的助言ではありません。</p>
          <ul className="divide-y divide-border">
            {findings.length === 0 && <li className="py-2 text-muted-foreground">ルールの判定はありません</li>}
            {findings.map((item) =>
              item.flags.map((flag) => (
                <li key={`${item.path}-${flag.rule_id}`} className="flex flex-wrap items-center gap-2 py-2">
                  <Badge tone={RESULT[flag.result].tone}>{RESULT[flag.result].label}</Badge>
                  <span className="font-mono text-[12px]">{flag.rule_id}</span>
                  <Badge>{SEVERITY[flag.severity]}</Badge>
                  <Truncate className="min-w-0 flex-1">{show(item.proposed_value)}</Truncate>
                </li>
              )),
            )}
          </ul>
        </Panel>
        {editable && (
          <Panel title="コメント">
            <Field label="コメント" hint="却下するときは理由を書いてください（2000 文字以内）。" {...form.field("comment", comment !== "")}>
              <textarea className="field-control" value={comment} onChange={(e) => setComment(e.target.value)} />
            </Field>
          </Panel>
        )}
      </div>
      <ConfirmDialog
        open={confirming !== null}
        onOpenChange={(open) => !open && setConfirming(null)}
        title={confirming ? `確認の決定：${DECISION[confirming]}` : "確認の決定"}
        confirmLabel={confirming ? `${DECISION[confirming]}する` : "決定する"}
        danger={confirming === "rejected"}
        busy={decide.busy}
        onConfirm={submit}
      >
        {confirming === "rejected" ? (
          <p>この実行を却下します。以降の処理は行われず、結果は出力されません。決定は取り消せません。</p>
        ) : (
          <p>
            {confirming === "approved_with_corrections" ? `${corrections.length} 件の修正を記録して` : ""}
            承認します。実行は次の処理へ進みます。決定は取り消せません。
          </p>
        )}
      </ConfirmDialog>
    </div>
  );
}

function Evidence({ item }: { item: Item }) {
  if (item.evidence.length === 0) {
    return <span className="mt-1 block text-[11px] text-muted-foreground">根拠：未確認（根拠がありません）</span>;
  }
  return (
    <ul className="mt-1 flex flex-wrap gap-1">
      {item.evidence.map((e) => (
        <li key={`${e.document_id}-${e.page}-${e.start}`} className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <span>
            {e.page} ページ {e.start}–{e.end}
          </span>
          {e.status === "verified" ? <Badge tone="success">照合済み</Badge> : <Badge tone="warning">未確認</Badge>}
        </li>
      ))}
    </ul>
  );
}
