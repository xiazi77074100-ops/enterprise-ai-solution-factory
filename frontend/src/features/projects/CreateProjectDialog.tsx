import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, type Schemas } from "../../api/client";
import { useApi } from "../../app/feedback";
import { Field, FormStatus, useFormCheck } from "../../components/Field";
import { Modal } from "../../components/Modal";
import { Button } from "../../components/ui";
import { firstError, maxLength, required } from "../../lib/validation";

const EMPTY = { name: "", businessDomain: "", description: "" };

export function CreateProjectDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const navigate = useNavigate();
  const call = useApi();
  const [f, setF] = useState(EMPTY);
  const form = useFormCheck({
    name: firstError(required(f.name, "プロジェクト名"), maxLength(f.name, 100, "プロジェクト名")),
    businessDomain: firstError(required(f.businessDomain, "業務区分"), maxLength(f.businessDomain, 50, "業務区分")),
    description: maxLength(f.description, 1000, "説明"),
  });

  const close = (next: boolean) => {
    if (!next) {
      setF(EMPTY);
      form.reset();
    }
    onOpenChange(next);
  };

  const save = async () => {
    const body: Schemas["ProjectCreate"] = {
      name: f.name.trim(),
      business_domain: f.businessDomain.trim(),
      ...(f.description.trim() ? { description: f.description.trim() } : {}),
    };
    const created = await call.run(() => api<Schemas["Project"]>("POST", "/api/v1/projects", { body }), "プロジェクトを作成しました。");
    if (created) {
      close(false);
      onCreated();
      navigate(`/projects/${created.id}`);
    }
  };

  return (
    <Modal
      open={open}
      onOpenChange={close}
      title="プロジェクトの作成"
      busy={call.busy}
      footer={
        <>
          <FormStatus problem={form.firstProblem} />
          <span className="flex-1" />
          <Button variant="ghost" onClick={() => close(false)}>
            取消
          </Button>
          <Button variant="default" disabled={!form.valid} loading={call.busy} onClick={save}>
            作成
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <Field label="プロジェクト名" required {...form.field("name", f.name !== "")}>
          <input className="field-control" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        </Field>
        <Field label="業務区分" required hint="例：経理、法務。表示用の分類で、処理の分岐には使いません。" {...form.field("businessDomain", f.businessDomain !== "")}>
          <input className="field-control" value={f.businessDomain} onChange={(e) => setF({ ...f, businessDomain: e.target.value })} />
        </Field>
        <Field label="説明" {...form.field("description", f.description !== "")}>
          <textarea className="field-control" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
        </Field>
      </div>
    </Modal>
  );
}
