# Forms

## Field anatomy

Each field should have a persistent, programmatically associated label. Put required markers next to the label and convey required state to assistive technology. Keep help text and validation feedback near the control; connect both with `aria-describedby`. Set `aria-invalid` for invalid values and use a clear focus ring.

Show an error that names the problem and, when possible, how to correct it. Avoid relying on color alone: pair a danger outline with readable error text. Do not show an error before the user has had a reasonable opportunity to enter a value, unless immediate feedback is important for the task.

## Submission

Validate at the point of entry and again at submission. When the product's validation model is local and complete, keep the primary submit action disabled until required values are valid; preserve a clear explanation of what needs attention. For server validation, pending requests, or multi-step workflows, use explicit submitting/error states rather than making the form appear inert.

Keep user-entered values when validation fails. Disabled and read-only controls should look distinct and remain understandable. Group related fields; use multiple columns only when their reading order remains clear at narrow widths.

## Demo reference

`Field.jsx` composes label, required mark, cloned control attributes, hint, and error. `useFormCheck` tracks touched fields and exposes `valid`, enabling `disabled={!form.valid}`. `theme.css` gives controls a 36px height, 13px text, visible focus treatment, and a red invalid border; errors use 12px text. These are implementation references, not requirements for every control or validation strategy.
