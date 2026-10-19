import { Download, FileUp, Files } from "lucide-react";
import { useState } from "react";

import { api, apiUpload, type Schemas } from "../../api/client";
import { useApi } from "../../app/feedback";
import { useLoad } from "../../app/useLoad";
import { Field, useFormCheck } from "../../components/Field";
import { EmptyRow, Panel } from "../../components/layout";
import { Modal } from "../../components/Modal";
import { Pagination, useCursorPagination } from "../../components/Pagination";
import { Truncate } from "../../components/Truncate";
import { Badge, Button, DownloadLink } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import type { Check } from "../../lib/validation";

export const UPLOAD_ROLES = ["solution_lead", "solution_architect", "qa_evaluator"];
const MAX_BYTES = 10 * 1024 * 1024;
// Same allowlist as the server (docs/design/detail/documents.md §4); the server also checks the file's first bytes.
const TYPES: Record<string, string> = { pdf: "application/pdf", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg" };
const TYPE_LABEL: Record<string, string> = { "application/pdf": "PDF", "image/png": "PNG", "image/jpeg": "JPEG" };

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function checkFile(file: File | null): Check {
  if (!file) return "ファイルを選択してください。";
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!TYPES[ext]) return "PDF・PNG・JPEG のファイルを選択してください。";
  if (file.size === 0) return "ファイルが空です。";
  if (file.size > MAX_BYTES) return "ファイルの大きさは 10 MB 以内にしてください。";
  return null;
}

export function DocumentsPanel({ projectId, myRoles }: { projectId: string; myRoles: string[] }) {
  const paging = useCursorPagination(projectId);
  const list = useLoad(
    () =>
      api<Schemas["DocumentPage"]>("GET", `/api/v1/projects/${encodeURIComponent(projectId)}/documents`, {
        query: { limit: paging.limit, cursor: paging.cursor },
      }),
    `${projectId}|${paging.limit}|${paging.cursor}`,
  );
  const [uploading, setUploading] = useState(false);
  const canUpload = myRoles.some((r) => UPLOAD_ROLES.includes(r));
  const rows = list.data?.items ?? [];

  return (
    <Panel
      title="文書"
      icon={Files}
      meta={list.data ? `${list.data.page.total} 件` : undefined}
      actions={
        canUpload && (
          <Button icon={<FileUp className="size-3.5" />} onClick={() => setUploading(true)}>
            登録
          </Button>
        )
      }
    >
      <div className="card overflow-hidden">
        <div className="relative overflow-x-auto">
          <table className="zebra w-full min-w-[720px] text-[13px]">
            <thead className="text-[12px] text-muted-foreground">
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-3 py-2 font-semibold">ファイル名</th>
                <th scope="col" className="px-3 py-2 font-semibold">形式</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">ページ</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">大きさ</th>
                <th scope="col" className="px-3 py-2 font-semibold">登録日時</th>
                <th scope="col" className="px-3 py-2 font-semibold"><span className="sr-only">操作</span></th>
              </tr>
            </thead>
            <tbody>
              {list.data && rows.length === 0 && <EmptyRow colSpan={6}>文書はまだ登録されていません</EmptyRow>}
              {rows.map((d) => (
                <tr key={d.id} className="border-b border-border last:border-0">
                  <td className="px-3 py-2">
                    <span className="flex items-center gap-2">
                      <Truncate className="max-w-[280px] font-semibold">{d.display_name}</Truncate>
                      <Badge tone="primary">合成データ</Badge>
                    </span>
                    <span className="block font-mono text-[11px] text-muted-foreground">{d.sha256.slice(0, 12)}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{TYPE_LABEL[d.media_type] ?? d.media_type}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{d.page_count}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">{formatBytes(d.size_bytes)}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatDateTime(d.created_at)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    <DownloadLink href={`/api/v1/documents/${encodeURIComponent(d.id)}/content`} icon={<Download className="size-3.5" />}>
                      ダウンロード
                    </DownloadLink>
                  </td>
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
      {uploading && (
        <UploadDialog
          projectId={projectId}
          onClose={() => setUploading(false)}
          onDone={() => {
            setUploading(false);
            list.reload();
          }}
        />
      )}
    </Panel>
  );
}

function UploadDialog({ projectId, onClose, onDone }: { projectId: string; onClose: () => void; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const upload = useApi();
  const form = useFormCheck({ file: checkFile(file) });

  const submit = async () => {
    if (!file) return;
    const body = new FormData();
    body.append("file", file, file.name);
    body.append("data_origin", "synthetic");
    const created = await upload.run(
      () => apiUpload<Schemas["Document"]>(`/api/v1/projects/${encodeURIComponent(projectId)}/documents`, body),
      "文書を登録しました。",
    );
    if (created) onDone();
  };

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title="文書の登録"
      busy={upload.busy}
      footer={
        <>
          <span className="flex-1 text-[12px] text-muted-foreground">{form.valid ? "" : form.firstProblem}</span>
          <Button variant="ghost" onClick={onClose}>
            取消
          </Button>
          <Button variant="default" disabled={!form.valid} loading={upload.busy} onClick={submit} icon={<FileUp className="size-4" />}>
            登録
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <Field
          label="ファイル"
          required
          hint="PDF・PNG・JPEG、10 MB・30 ページまで。検証用の合成データだけを登録できます。"
          {...form.field("file", file !== null)}
        >
          <input
            type="file"
            className="field-control"
            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </Field>
      </div>
    </Modal>
  );
}
