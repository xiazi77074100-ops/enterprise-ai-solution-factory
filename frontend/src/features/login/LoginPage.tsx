import { ArrowRight, Factory, Lock } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../app/auth";
import { useApi } from "../../app/feedback";
import { Field, useFormCheck } from "../../components/Field";
import { Button } from "../../components/ui";
import { maxLength, firstError, required } from "../../lib/validation";

// Login scene follows the sales-assistant UI (D-026): the only screen with brand color on the background.
export function LoginPage() {
  const { session, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const api = useApi();
  const [f, setF] = useState({ loginId: "", password: "" });
  const form = useFormCheck({
    loginId: firstError(required(f.loginId, "ユーザー ID"), maxLength(f.loginId, 64, "ユーザー ID")),
    password: firstError(required(f.password, "パスワード"), maxLength(f.password, 128, "パスワード")),
  });

  if (session) return <Navigate to="/projects" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.valid) return;
    const ok = await api.run(async () => {
      await login(f.loginId, f.password);
      return true;
    });
    if (ok) {
      const from = (location.state as { from?: string } | null)?.from;
      // Only internal paths (no open redirect): must start with a single "/".
      navigate(from && /^\/(?!\/)/.test(from) ? from : "/projects", { replace: true });
    } else {
      setF((v) => ({ ...v, password: "" }));
    }
  };

  return (
    <div className="login-scene relative flex min-h-full items-center justify-center overflow-hidden p-6">
      <div aria-hidden="true" className="login-wash pointer-events-none absolute inset-0" />
      <div aria-hidden="true" className="login-dots pointer-events-none absolute inset-0" />
      <div className="relative w-full max-w-[400px]">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-white/95 shadow-lg shadow-black/20" style={{ color: "var(--deep)" }}>
            <Factory className="size-5" aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-[18px] font-bold leading-tight tracking-tight text-white">EASF</h1>
            <p className="text-[12px] text-white/75">Enterprise AI Solution Factory ── AI 部品の組立と再利用</p>
          </div>
        </div>
        <form onSubmit={submit} className="card flex flex-col gap-3 p-5 shadow-xl shadow-black/10" noValidate>
          <p className="text-[13px] font-semibold">ログイン</p>
          <Field label="ユーザー ID" required {...form.field("loginId", f.loginId !== "")}>
            <input
              className="field-control"
              autoComplete="username"
              value={f.loginId}
              onChange={(e) => setF({ ...f, loginId: e.target.value })}
            />
          </Field>
          <Field label="パスワード" required {...form.field("password", f.password !== "")}>
            <input
              className="field-control pr-8"
              type="password"
              autoComplete="current-password"
              value={f.password}
              onChange={(e) => setF({ ...f, password: e.target.value })}
            />
          </Field>
          <Button type="submit" variant="default" className="mt-1 h-9 w-full" disabled={!form.valid} loading={api.busy}>
            ログイン <ArrowRight className="size-3.5" aria-hidden="true" />
          </Button>
          <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-snug text-muted-foreground">
            <Lock className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
            検証用の環境です（本番利用不可）。データは合成データだけを使います。
          </p>
        </form>
      </div>
      <p className="absolute inset-x-0 bottom-0 py-2 text-center text-[11px] text-white/60">EASF — 個人の検証用 POC</p>
    </div>
  );
}
