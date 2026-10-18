---
name: japan-enterprise-frontend
description: Design and implement reusable Japanese enterprise web interfaces, especially dense operational screens with dashboards, tables, forms, navigation, status, and dialogs. Use the current product's source code and design system as primary evidence; adapt principles instead of copying another product's branding or business data.
---

# Japan Enterprise Frontend

Use this skill when designing or changing a Japanese business application UI. It distills patterns verified in the sales-assistant demo implementation; it is not a mandate to copy that demo's colors, labels, data, or architecture.

## Evidence-first workflow

1. Inspect the target repository before proposing visuals: theme/tokens, global CSS, app shell/layout, shared components, and representative dashboard, list, detail, and form implementations.
2. Record which patterns are already intentional and reusable. Prefer the existing system and components over a parallel design system.
3. Use the references below for decisions. Values identified as **demo reference** describe the inspected implementation and are starting points, not universal requirements.
4. Implement the smallest coherent change. Preserve existing interaction, permission, responsive, and accessibility behavior.
5. Review the complete states: normal, hover/focus, disabled, validation error, empty, loading, and narrow viewport where relevant.

## Reusable principles

- Treat the app shell, navigation, page context, filters, content, and actions as one workflow. Keep the current location and the next useful action easy to find.
- Build visual hierarchy from a small set of type roles, spacing steps, surface levels, and semantic colors. Do not add one-off colors or sizes without a clear role.
- Optimize dense screens for scanning: stable column alignment, concise labels, tabular numbers, restrained row striping, and intentional truncation with access to the full value.
- Make state understandable through text or icon as well as color. Keep role/brand color separate from success, warning, and danger meaning.
- Forms should state what is required, associate labels and errors with controls, explain how to fix invalid values, and prevent invalid submission when the product's validation model allows it.
- Prefer shared components for repeated patterns. Extract only when the pattern is genuinely repeated or needs consistent behavior.
- Use Japanese business language that names the action and its result plainly. Avoid unexplained abbreviations, ambiguous status words, and unnecessarily technical wording.
- Keep decoration subordinate to information. Motion must be brief, useful, and disabled or reduced for `prefers-reduced-motion` users.

## References

- [Design tokens](references/design-tokens.md)
- [Layout](references/layout.md)
- [Typography](references/typography.md)
- [Tables](references/tables.md)
- [Forms](references/forms.md)
- [Dashboard](references/dashboard.md)
- [Japanese UI](references/japanese-ui.md)
- [Components](references/components.md)
- [Quality gate](references/quality-gate.md)

## Inspected implementation

The observations were grounded in `src/versions/shadcn/theme.css` and the shared components `layout.jsx`, `ui.jsx`, `Field.jsx`, `StatTile.jsx`, `Sidebar.jsx`, `Truncate.jsx`, `Pagination.jsx`, and `Modal.jsx`, plus representative `DealsList.jsx`, `CustomerList.jsx`, and `Dashboard.jsx` implementations. Re-check these files if using this skill inside this repository; implementation details can change.
