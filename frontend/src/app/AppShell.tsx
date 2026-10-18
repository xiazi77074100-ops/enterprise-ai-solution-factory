import { clsx } from "clsx";
import { Boxes, ClipboardCheck, Factory, FolderKanban, LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { Badge, Button } from "../components/ui";
import { useAuth } from "./auth";
import { useApi } from "./feedback";

// Shell layout follows the sales-assistant UI (D-026): grouped deep sidebar, light gradient header band.
const GROUPS = [
  {
    label: "業務",
    items: [
      { to: "/projects", label: "プロジェクト一覧", icon: FolderKanban },
      { to: "/reviews", label: "確認タスク", icon: ClipboardCheck },
    ],
  },
  { label: "部品", items: [{ to: "/catalog", label: "能力カタログ", icon: Boxes }] },
];

export function AppShell() {
  const { session, loading, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const api = useApi();

  if (loading) return <p className="p-6 text-muted-foreground" role="status">読み込み中…</p>;
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  const wide = !collapsed || mobileOpen;
  const toggleLabel = wide ? "メニューを折りたたむ" : "メニューを開く";
  const name = session.user.display_name;

  return (
    <div className="flex h-full min-h-0">
      <aside
        id="app-sidebar"
        className={clsx(
          "app-sidebar fixed inset-y-0 left-0 z-50 shrink-0 flex-col transition-[width] duration-300 md:static md:flex",
          mobileOpen ? "flex w-56" : "hidden",
          collapsed ? "md:w-[60px]" : "md:w-56",
        )}
        aria-label="メニュー"
      >
        <div className={clsx("flex items-center gap-2 py-3", wide ? "px-3" : "justify-center")}>
          <button
            type="button"
            onClick={() => (mobileOpen ? setMobileOpen(false) : setCollapsed((v) => !v))}
            aria-label={toggleLabel}
            title={toggleLabel}
            aria-expanded={wide}
            aria-controls="app-sidebar"
            className="flex size-8 shrink-0 items-center justify-center rounded-md border border-white/30 bg-white/10 text-white hover:bg-white/20"
          >
            <Menu className="size-4" aria-hidden="true" />
          </button>
          {wide && (
            <>
              <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-white shadow-sm" style={{ color: "var(--deep)" }}>
                <Factory className="size-4" aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-bold leading-tight">EASF</span>
                <span className="block truncate text-[11px] leading-tight text-muted-foreground">AI 部品の組立と再利用</span>
              </span>
            </>
          )}
        </div>
        <nav className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
          {GROUPS.map((group) => (
            <div key={group.label} className="mb-3">
              {wide ? (
                <p className="px-2 pb-1 text-[11px] font-semibold tracking-wide text-muted-foreground">{group.label}</p>
              ) : (
                <div className="mx-2 mb-1 h-px bg-white/20" />
              )}
              <div className="space-y-0.5">
                {group.items.map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    title={label}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      clsx(
                        "nav-item flex h-9 items-center rounded-md text-[13px] transition-colors",
                        wide ? "gap-2 px-2" : "justify-center",
                        isActive && "nav-active",
                      )
                    }
                  >
                    <Icon className="size-4 shrink-0" aria-hidden="true" />
                    {wide ? <span className="truncate">{label}</span> : <span className="sr-only">{label}</span>}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/30 md:hidden" aria-hidden="true" onClick={() => setMobileOpen(false)} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="app-header flex h-12 shrink-0 items-center gap-2 px-3">
          <Button
            variant="ghost"
            className="md:hidden"
            aria-label="メニューを開く"
            aria-expanded={mobileOpen}
            aria-controls="app-sidebar"
            onClick={() => setMobileOpen(true)}
            icon={<Menu className="size-4" />}
          />
          <Badge tone="warning">検証用（本番利用不可）</Badge>
          <span className="flex-1" />
          <span className="hidden max-w-[30vw] truncate text-[12px] text-muted-foreground sm:inline">{name}</span>
          <span
            className="flex size-8 shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white"
            style={{ background: "var(--deep)" }}
            title={name}
            aria-hidden="true"
          >
            {name.slice(0, 1)}
          </span>
          <Button variant="ghost" loading={api.busy} onClick={() => api.run(logout)} icon={<LogOut className="size-4" />}>
            <span className="hidden sm:inline">ログアウト</span>
            <span className="sr-only sm:hidden">ログアウト</span>
          </Button>
        </header>
        <main className="page-host flex min-h-0 flex-1 flex-col overflow-auto">
          <div key={location.pathname} className="flex min-h-0 flex-1 flex-col">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
