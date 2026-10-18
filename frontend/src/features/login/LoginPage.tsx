import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../app/auth";
import { useApi } from "../../app/feedback";
import { Field, useFormCheck } from "../../components/Field";
import { Button } from "../../components/ui";
import { maxLength, firstError, required } from "../../lib/validation";

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
    <div className="grid min-h-full place-items-center p-4">
      <form onSubmit={submit} className="card flex w-[min(92vw,380px)] flex-col gap-4 p-6" noValidate>
        <div>
          <h1 className="page-title">EASF</h1>
          <p className="text-[12px] text-muted-foreground">Enterprise AI Solution Factory（検証用）</p>
        </div>
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
            className="field-control"
            type="password"
            autoComplete="current-password"
            value={f.password}
            onChange={(e) => setF({ ...f, password: e.target.value })}
          />
        </Field>
        <Button type="submit" variant="default" className="h-9" disabled={!form.valid} loading={api.busy}>
          ログイン
        </Button>
      </form>
    </div>
  );
}
