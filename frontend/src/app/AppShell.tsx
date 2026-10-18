import { clsx } from "clsx";
import { Boxes, FolderKanban, LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { Badge, Button } from "../components/ui";
import { useAuth } from "./auth";
import { useApi } from "./feedback";

const NAV = [
  { to: "/projects", label: "プロジェクト一覧", icon: FolderKanban },
  { to: "/catalog", label: "能力カタログ", icon: Boxes },
];

export function AppShell() {
  const { session, loading, logout } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const api = useApi();

  if (loading) return <p className="p-6 text-muted-foreground" role="status">読み込み中…</p>;
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex h-full min-h-0">
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-56 shrink-0 flex-col bg-sidebar text-sidebar-foreground md:static md:flex",
          open ? "flex" : "hidden",
        )}
        aria-label="メニュー"
      >
        <div className="flex h-12 items-center px-4 text-[15px] font-bold">EASF</div>
        <nav className="flex flex-col gap-0.5 px-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                clsx("flex h-9 items-center gap-2 rounded-md px-3 text-[13px]", isActive ? "bg-white/15 font-semibold" : "hover:bg-white/10")
              }
            >
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border bg-card px-3">
          <Button
            variant="ghost"
            className="md:hidden"
            aria-label="メニューを開く"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            icon={<Menu className="size-4" />}
          />
          <Badge tone="warning">検証用（本番利用不可）</Badge>
          <span className="flex-1" />
          <span className="max-w-[40vw] truncate text-[12px] text-muted-foreground">{session.user.display_name}</span>
          <Button variant="ghost" loading={api.busy} onClick={() => api.run(logout)} icon={<LogOut className="size-4" />}>
            ログアウト
          </Button>
        </header>
        <main className="flex min-h-0 flex-1 flex-col overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
