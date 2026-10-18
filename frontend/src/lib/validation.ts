// Field checks with the wording rules of ui-design §5.1. Mirror the server rules; the server stays authoritative.
export type Check = string | null;

export function required(value: string, label: string, verb: "入力" | "選択" = "入力"): Check {
  return value.trim() === "" ? `${label}を${verb}してください。` : null;
}

export function maxLength(value: string, max: number, label: string): Check {
  return value.length > max ? `${label}は${max}文字以内で入力してください。` : null;
}

export function firstError(...checks: Check[]): Check {
  return checks.find((c) => c !== null) ?? null;
}
