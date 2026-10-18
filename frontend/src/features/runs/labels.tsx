// Japanese labels and badges for runs, nodes, trace events and reviews (ui-design §7・§8).
// The execution mode always comes from the API's execution_mode; the screen never decides it.
import type { Schemas } from "../../api/client";
import { Badge, type Tone } from "../../components/ui";

type RunStatus = Schemas["RunStatus"];
type NodeStatus = Schemas["NodeRun"]["status"];

export const RUN_STATUS: Record<RunStatus, { label: string; tone: Tone }> = {
  pending: { label: "受付", tone: "neutral" },
  running: { label: "実行中", tone: "primary" },
  waiting_review: { label: "確認待ち", tone: "warning" },
  succeeded: { label: "成功", tone: "success" },
  rejected: { label: "却下", tone: "danger" },
  failed: { label: "失敗", tone: "danger" },
  cancelled: { label: "取消", tone: "neutral" },
};

export const NODE_STATUS: Record<NodeStatus, { label: string; tone: Tone }> = {
  pending: { label: "未実行", tone: "neutral" },
  running: { label: "実行中", tone: "primary" },
  waiting_review: { label: "確認待ち", tone: "warning" },
  succeeded: { label: "成功", tone: "success" },
  failed: { label: "失敗", tone: "danger" },
  skipped: { label: "省略", tone: "neutral" },
};

export const SOLUTION_STATE: Record<Schemas["Solution"]["state"], { label: string; tone: Tone }> = {
  draft: { label: "下書き", tone: "neutral" },
  validated: { label: "検証済み", tone: "primary" },
  approved: { label: "承認済み", tone: "success" },
  archived: { label: "保管", tone: "neutral" },
};

/** failure_code / error_code → what happened, in words (codes stay visible for support). */
export const FAILURE: Record<string, string> = {
  node_failed: "処理が失敗しました",
  timeout: "時間内に終わりませんでした",
  budget_exceeded: "予算（時間・トークン・費用）を超えました",
  invalid_input: "入力が形式に合いません",
  invalid_output: "出力が形式に合いません",
  output_too_large: "出力が大きすぎます",
  no_reviewer: "確認者がいません",
  implementation_unavailable: "実装がまだありません",
  interrupted: "処理が中断されました",
  crashed: "処理が異常終了しました",
  rejected: "確認で却下されました",
  workflow_changed: "解決策が変更されました",
};

export const EVENT: Record<string, string> = {
  "run.started": "実行の受付",
  "node.started": "処理の開始",
  "node.completed": "処理の完了",
  "node.failed": "処理の失敗",
  "review.requested": "確認の依頼",
  "review.completed": "確認の決定",
  "run.completed": "実行の終了",
  "run.failed": "実行の失敗",
};

export const DECISION: Record<string, string> = {
  approved: "承認",
  approved_with_corrections: "修正して承認",
  rejected: "却下",
};

export const RESULT: Record<"fail" | "pass" | "uncertain", { label: string; tone: Tone }> = {
  fail: { label: "該当あり", tone: "danger" },
  pass: { label: "該当なし", tone: "success" },
  uncertain: { label: "不明", tone: "warning" },
};

export const SEVERITY: Record<string, string> = { critical: "重大", major: "重要", minor: "軽微" };

export function StatusBadge({ status }: { status: RunStatus }) {
  const s = RUN_STATUS[status];
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

export function NodeStatusBadge({ status }: { status: NodeStatus }) {
  const s = NODE_STATUS[status];
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

/** 「実行」or「模擬（MOCK）」(mixed: 一部模擬). Text, not only color. */
export function ModeBadge({ mode }: { mode: "real" | "mock" | "mixed" }) {
  if (mode === "real") return <Badge tone="neutral">実行</Badge>;
  return <Badge tone="mock">{mode === "mock" ? "模擬（MOCK）" : "一部模擬（MOCK）"}</Badge>;
}

export function failureText(code: string | null | undefined): string | null {
  if (!code) return null;
  return FAILURE[code] ?? (code.startsWith("exception_") ? "処理で例外が発生しました" : "処理が失敗しました");
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}
