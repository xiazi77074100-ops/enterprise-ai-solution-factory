# Quality gate

Review the implementation in the running application where possible. Check:

## Visual and responsive

- Is hierarchy obvious without relying on decoration?
- Do shell, content, panel, table, and form align to a consistent spacing system?
- Do representative short and long Japanese labels fit at desktop and narrow widths?
- Is horizontal scrolling limited to the content that needs it?
- Do sticky elements, dialogs, and tooltips layer and scroll correctly?

## Behavior and states

- Do primary actions, filters, sorting, pagination, and row actions work as labelled?
- Are active filters and selected navigation states visible?
- Are empty, loading, error, disabled, and validation states distinguishable?
- Does invalid form submission explain what to fix and preserve entered data?
- Do hover effects imply only interactions that are actually available?

## Accessibility

- Can controls be reached and used by keyboard, with a visible focus indicator?
- Are headings ordered, labels associated, errors announced, and icon-only controls named?
- Is state communicated with text/icon in addition to color?
- Is contrast sufficient in light and dark modes, including focus and disabled states?
- Does reduced-motion preference suppress nonessential animation?

## Evidence and scope

- Did the implementation use the target app's existing theme and shared components?
- Are one-off tokens, abstractions, and dependencies justified by repeated need?
- Were product-specific customer names, records, logos, and mock data kept out of reusable guidance?
- If a pattern was inferred rather than directly implemented, is that distinction clear?
