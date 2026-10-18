import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { firstError, maxLength, required } from "../lib/validation";
import { Field, useFormCheck } from "./Field";
import { Button } from "./ui";

function Form() {
  const [name, setName] = useState("");
  const form = useFormCheck({ name: firstError(required(name, "氏名"), maxLength(name, 5, "氏名")) });
  return (
    <>
      <Field label="氏名" required {...form.field("name", name !== "")}>
        <input className="field-control" value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Button disabled={!form.valid}>保存</Button>
    </>
  );
}

describe("ui-design §5.1 form rules", () => {
  it("keeps the primary button disabled until the input is valid", async () => {
    render(<Form />);
    const save = screen.getByRole("button", { name: "保存" });
    expect(save).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/氏名/), "山田");
    expect(save).toBeEnabled();
    await userEvent.type(screen.getByLabelText(/氏名/), "太郎さん");
    expect(save).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("氏名は5文字以内で入力してください。");
  });

  it("shows the required error only after leaving an empty field, with aria-invalid", async () => {
    render(<Form />);
    const input = screen.getByLabelText(/氏名/);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(input).toHaveAttribute("aria-required", "true");
    await userEvent.click(input);
    await userEvent.tab();
    expect(screen.getByRole("alert")).toHaveTextContent("氏名を入力してください。");
    expect(input).toHaveAttribute("aria-invalid", "true");
  });

  it("marks required fields with a red asterisk instead of （必須）", () => {
    render(<Form />);
    expect(screen.getByText("*")).toHaveClass("text-danger-ink");
    expect(screen.queryByText(/必須/)).toBeNull();
  });
});
