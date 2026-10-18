import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "./ui";

/** ui-design §5.3: Esc and focus handling by Radix; the background is not blurred. */
export function Modal({
  open,
  onOpenChange,
  title,
  footer,
  busy = false,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  footer: ReactNode;
  busy?: boolean;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[100] bg-black/30" />
        <Dialog.Content
          aria-describedby={undefined}
          className="card fixed left-1/2 top-[10vh] z-[110] flex max-h-[80vh] w-[min(94vw,560px)] -translate-x-1/2 flex-col"
        >
          <div className="panel-head">
            <Dialog.Title className="panel-title">{title}</Dialog.Title>
            <span className="flex-1" />
            <Dialog.Close asChild>
              <button type="button" className="grid size-8 place-items-center rounded hover:bg-muted" aria-label="閉じる" disabled={busy}>
                <X className="size-4" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>
          <div className="relative min-h-0 flex-1 overflow-auto p-4">
            {children}
            {busy && (
              <div className="absolute inset-0 grid place-items-center bg-card/70 text-[13px]" role="status">
                処理中…
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-border px-4 py-3">{footer}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Confirmation for irreversible or weighty operations (approve, delete …). Never window.confirm. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  confirmLabel,
  danger = false,
  busy,
  onConfirm,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  confirmLabel: string;
  danger?: boolean;
  busy: boolean;
  onConfirm: () => void;
  children: ReactNode;
}) {
  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      busy={busy}
      footer={
        <>
          <span className="flex-1" />
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={busy}>
            取消
          </Button>
          <Button variant={danger ? "dangerSolid" : "default"} loading={busy} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="text-[13px]">{children}</div>
    </Modal>
  );
}
