import { Braces, Info } from "lucide-react";
import { useParams } from "react-router-dom";

import { api, type Schemas } from "../../api/client";
import { useLoad } from "../../app/useLoad";
import { PageHeader, Panel } from "../../components/layout";
import { Badge, VersionTag } from "../../components/ui";
import { formatDateTime } from "../../lib/format";
import { KIND_LABELS } from "./labels";

type Contract = {
  description?: string;
  implementation?: { ref?: string };
  provenance?: { source?: string; license?: string; author?: string };
  tags?: string[];
  timeout_ms?: number;
  retry?: { max_attempts?: number; idempotent?: boolean };
  input_schema?: unknown;
  output_schema?: unknown;
  configuration_schema?: unknown;
};

export function CapabilityDetailPage() {
  const { capabilityId = "", version = "" } = useParams();
  const { data, error } = useLoad(
    () =>
      api<Schemas["CapabilityVersion"]>(
        "GET",
        `/api/v1/capabilities/${encodeURIComponent(capabilityId)}/versions/${encodeURIComponent(version)}`,
      ),
    `${capabilityId}@${version}`,
  );
  const c = (data?.contract ?? {}) as Contract;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 border-b border-border bg-background px-4 py-3">
        <PageHeader
          title={data?.name ?? capabilityId}
          titleVisible
          breadcrumb={{ label: "能力カタログ", to: "/catalog", current: `${capabilityId}@${version}` }}
        >
          <span className="flex flex-wrap items-center gap-2">
            <VersionTag id={capabilityId} version={version} />
            {data && <Badge tone="primary">{KIND_LABELS[data.kind] ?? data.kind}</Badge>}
            <Badge>変更不可の版</Badge>
          </span>
        </PageHeader>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
        {error && (
          <p role="status" className="card px-3 py-2 text-[12px] text-danger-ink">
            {error.message}
          </p>
        )}
        {data && (
          <>
            <Panel title="概要" icon={Info}>
              <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-[13px] sm:grid-cols-[160px_1fr]">
                <dt className="text-[12px] text-muted-foreground">説明</dt>
                <dd>{c.description}</dd>
                <dt className="text-[12px] text-muted-foreground">実装の参照</dt>
                <dd className="break-all font-mono text-[12px]">{c.implementation?.ref}</dd>
                <dt className="text-[12px] text-muted-foreground">タイムアウト・再試行</dt>
                <dd>
                  {((c.timeout_ms ?? 0) / 1000).toLocaleString("ja-JP")} 秒・最大 {c.retry?.max_attempts ?? 0} 回
                  {c.retry?.idempotent ? "（冪等）" : "（再試行なし）"}
                </dd>
                <dt className="text-[12px] text-muted-foreground">出所・ライセンス</dt>
                <dd>
                  {c.provenance?.source}・{c.provenance?.license}・{c.provenance?.author}
                </dd>
                <dt className="text-[12px] text-muted-foreground">タグ</dt>
                <dd className="flex flex-wrap gap-1">
                  {(c.tags ?? []).map((t) => (
                    <Badge key={t}>{t}</Badge>
                  ))}
                </dd>
                <dt className="text-[12px] text-muted-foreground">内容のハッシュ</dt>
                <dd className="break-all font-mono text-[11px]">{data.content_sha256}</dd>
                <dt className="text-[12px] text-muted-foreground">登録日時</dt>
                <dd className="tabular-nums">{formatDateTime(data.registered_at)}</dd>
              </dl>
            </Panel>
            {(
              [
                ["入力の契約", c.input_schema],
                ["出力の契約", c.output_schema],
                ["設定の契約", c.configuration_schema],
              ] as const
            ).map(([title, schema]) => (
              <Panel key={title} title={title} icon={Braces}>
                {/* Plain text only: contract JSON is never rendered as HTML. */}
                <pre className="max-h-[360px] overflow-auto rounded bg-muted p-3 font-mono text-[12px]">
                  {JSON.stringify(schema, null, 2)}
                </pre>
              </Panel>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
