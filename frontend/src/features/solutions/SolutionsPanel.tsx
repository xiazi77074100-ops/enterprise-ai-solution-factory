import { CheckCircle2, Play, ShieldCheck, Workflow } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, newIdempotencyKey, type Schemas } from "../../api/client";
import { useApi } from "../../app/feedback";
import { useLoad } from "../../app/useLoad";
import { Field, useFormCheck } from "../../components/Field";
import { EmptyRow, Panel } from "../../components/layout";
import { ConfirmDialog, Modal } from "../../components/Modal";
import { Pagination, useCursorPagination } from "../../components/Pagination";
import { Truncate } from "../../components/Truncate";
import { Badge, Button } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { firstError, maxLength, required, type Check } from "../../lib/validation";
import { SOLUTION_STATE } from "../runs/labels";

type Solution = Schemas["Solution"];
type WorkflowInput = { name: string; type: "document_ref" | "string" | "integer" | "boolean" };
type WorkflowDoc = { name?: string; workflow_id?: string; version?: number; nodes?: unknown[]; inputs?: WorkflowInput[] };

function doc(s: Solution): WorkflowDoc {
  return s.workflow as WorkflowDoc;
}

export function SolutionsPanel({ projectId, myRoles }: { projectId: string; myRoles: string[] }) {
  const paging = useCursorPagination(projectId);
  const list = useLoad(
    () =>
      api<Schemas["SolutionPage"]>("GET", `/api/v1/projects/${encodeURIComponent(projectId)}/solutions`, {
        query: { limit: paging.limit, cursor: paging.cursor },
      }),
    `${projectId}|${paging.limit}|${paging.cursor}`,
  );
  const validate = useApi();
  const approve = useApi();
  const [approving, setApproving] = useState<Solution | null>(null);
  const [starting, setStarting] = useState<Solution | null>(null);
  const isArchitect = myRoles.includes("solution_architect");
  const isLead = myRoles.includes("solution_lead");
  const canRun = isLead || isArchitect || myRoles.includes("qa_evaluator");

  const doValidate = async (s: Solution) => {
    const report = await validate.run(() =>
      api<Schemas["ValidationReport"]>("POST", `/api/v1/solutions/${encodeURIComponent(s.id)}/validate`),
    );
    if (report) list.reload();
  };
  const doApprove = async () => {
    if (!approving) return;
    const done = await approve.run(
      () => api("POST", `/api/v1/solutions/${encodeURIComponent(approving.id)}/approve`),
      "解決策を承認しました。",
    );
    if (done) {
      setApproving(null);
      list.reload();
    }
  };

  const rows = list.data?.items ?? [];
  return (
    <Panel title="解決策" icon={Workflow} meta={list.data ? `${list.data.page.total} 件` : undefined}>
      <p className="mb-3 text-[12px] text-muted-foreground">
        処理の流れ（Workflow）は API で登録します。承認された解決策だけを実行できます。
      </p>
      <div className="card overflow-hidden">
        <div className="relative overflow-x-auto">
          <table className="zebra w-full min-w-[640px] text-[13px]">
            <thead className="text-[12px] text-muted-foreground">
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-3 py-2 font-semibold">名前</th>
                <th scope="col" className="px-3 py-2 font-semibold">状態</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">処理数</th>
                <th scope="col" className="px-3 py-2 font-semibold">作成日時</th>
                <th scope="col" className="px-3 py-2 font-semibold"><span className="sr-only">操作</span></th>
              </tr>
            </thead>
            <tbody>
              {list.data && rows.length === 0 && <EmptyRow colSpan={5}>解決策はまだありません</EmptyRow>}
              {rows.map((s) => {
                const w = doc(s);
                const state = SOLUTION_STATE[s.state];
                return (
                  <tr key={s.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2">
                      <Truncate className="max-w-[260px] font-semibold">{w.name ?? "（名前なし）"}</Truncate>
                      <span className="block font-mono text-[11px] text-muted-foreground">
                        {w.workflow_id ?? "—"} 版 {w.version ?? "—"}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Badge tone={state.tone}>{state.label}</Badge>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{w.nodes?.length ?? 0}</td>
                    <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(s.created_at)}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-right">
                      <span className="inline-flex gap-1">
                        {isArchitect && s.state === "draft" && (
                          <Button icon={<ShieldCheck className="size-3.5" />} loading={validate.busy} onClick={() => doValidate(s)}>
                            検証
                          </Button>
                        )}
                        {isLead && s.state === "validated" && (
                          <Button icon={<CheckCircle2 className="size-3.5" />} onClick={() => setApproving(s)}>
                            承認
                          </Button>
                        )}
                        {canRun && s.state === "approved" && (
                          <Button icon={<Play className="size-3.5" />} onClick={() => setStarting(s)}>
                            実行
                          </Button>
                        )}
                      </span>
                    </td>
                  </tr>
                );
              })}
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
      <ConfirmDialog
        open={approving !== null}
        onOpenChange={(open) => !open && setApproving(null)}
        title="解決策の承認"
        confirmLabel="承認する"
        busy={approve.busy}
        onConfirm={doApprove}
      >
        <p>「{approving ? doc(approving).name : ""}」を承認します。承認後は処理の流れを変更できません。</p>
        <p className="mt-2 text-[12px] text-muted-foreground">作成者本人は承認できません。要件の版が承認済みである必要があります。</p>
      </ConfirmDialog>
      {starting && <StartRunDialog solution={starting} onClose={() => setStarting(null)} />}
    </Panel>
  );
}

function checkInput(input: WorkflowInput, value: string): Check {
  if (input.type === "boolean") return null;
  const label = `入力「${input.name}」`;
  if (input.type === "document_ref") return required(value, `${label}の文書`, "選択");
  const empty = required(value, label);
  if (empty) return empty;
  if (input.type === "integer") return /^-?\d{1,15}$/.test(value.trim()) ? null : `${label}の形式が正しくありません（例：120）。`;
  return maxLength(value, 10000, label);
}

function StartRunDialog({ solution, onClose }: { solution: Solution; onClose: () => void }) {
  const inputs = doc(solution).inputs ?? [];
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(inputs.map((i) => [i.name, i.type === "boolean" ? "false" : ""])),
  );
  const [confirming, setConfirming] = useState(false);
  const [key] = useState(newIdempotencyKey); // one key per dialog: a retried submit returns the same run
  const start = useApi();
  const navigate = useNavigate();
  const needsDocument = inputs.some((i) => i.type === "document_ref");
  const documents = useLoad(
    () =>
      needsDocument
        ? api<Schemas["DocumentPage"]>("GET", `/api/v1/projects/${encodeURIComponent(solution.project_id)}/documents`, {
            query: { limit: 200 },
          })
        : Promise.resolve(null),
    `${solution.project_id}|${needsDocument}`,
  );
  const form = useFormCheck(Object.fromEntries(inputs.map((i) => [i.name, firstError(checkInput(i, values[i.name] ?? ""))])));

  const payload = Object.fromEntries(
    inputs.map((i) => {
      const v = values[i.name] ?? "";
      return [i.name, i.type === "integer" ? Number(v) : i.type === "boolean" ? v === "true" : v];
    }),
  );
  const submit = async () => {
    const run = await start.run(
      () =>
        api<Schemas["Run"]>("POST", `/api/v1/solutions/${encodeURIComponent(solution.id)}/runs`, {
          body: { inputs: payload },
          headers: { "Idempotency-Key": key },
        }),
      "実行を受け付けました。",
    );
    if (run) navigate(`/runs/${run.id}`);
  };

  return (
    <>
      <Modal
        open={!confirming}
        onOpenChange={(open) => !open && onClose()}
        title="解決策の実行"
        busy={start.busy}
        footer={
          <>
            <span className="flex-1 text-[12px] text-muted-foreground">{form.valid ? "" : form.firstProblem}</span>
            <Button variant="ghost" onClick={onClose}>
              取消
            </Button>
            <Button variant="default" disabled={!form.valid} onClick={() => setConfirming(true)} icon={<Play className="size-4" />}>
              実行
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          <p className="text-[12px] text-muted-foreground">「{doc(solution).name}」を、次の入力で実行します。</p>
          {inputs.map((input) => (
            <Field key={input.name} label={input.name} required={input.type !== "boolean"} {...form.field(input.name, (values[input.name] ?? "") !== "")}>
              {input.type === "document_ref" ? (
                <select
                  className="field-control"
                  value={values[input.name]}
                  onChange={(e) => setValues((v) => ({ ...v, [input.name]: e.target.value }))}
                >
                  <option value="">（文書を選択）</option>
                  {(documents.data?.items ?? []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.display_name}（{formatDateTime(d.created_at)}）
                    </option>
                  ))}
                </select>
              ) : input.type === "boolean" ? (
                <select
                  className="field-control w-auto"
                  value={values[input.name]}
                  onChange={(e) => setValues((v) => ({ ...v, [input.name]: e.target.value }))}
                >
                  <option value="true">はい</option>
                  <option value="false">いいえ</option>
                </select>
              ) : (
                <input
                  className="field-control"
                  inputMode={input.type === "integer" ? "numeric" : undefined}
                  value={values[input.name]}
                  onChange={(e) => setValues((v) => ({ ...v, [input.name]: e.target.value }))}
                />
              )}
            </Field>
          ))}
        </div>
      </Modal>
      <ConfirmDialog
        open={confirming}
        onOpenChange={(open) => !open && setConfirming(false)}
        title="実行の開始"
        confirmLabel="実行する"
        busy={start.busy}
        onConfirm={submit}
      >
        <p>「{doc(solution).name}」の実行を開始します。開始した実行は取り消せません。</p>
      </ConfirmDialog>
    </>
  );
}
