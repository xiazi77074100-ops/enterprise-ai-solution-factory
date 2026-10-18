# Reusable components

## Component boundaries

Prefer a small shared vocabulary for patterns that recur: app shell/navigation, page header, panel, button/input/select, field, status badge, table helpers, pagination, empty/loading/error states, and dialog. Reuse a component when it centralizes either a repeated visual pattern or meaningful behavior. Do not create a wrapper for a one-off element without a clear benefit.

Keep components accessible by default: semantic elements, keyboard behavior, labels, focus management, and state attributes should be part of the component contract. Prefer native controls where they meet the need; use a library for complex behavior such as accessible menus, comboboxes, or dialogs rather than rebuilding it casually.

## Common contracts

- **App shell / sidebar:** current location, collapse state, accessible labels/tooltips for icon-only navigation.
- **Page header:** one page heading, optional scope/count/help, and primary actions.
- **Panel:** semantic heading level, optional metadata/actions, consistent header and body separation.
- **Form field:** label, required state, control, hint, and error relationships.
- **Status badge:** semantic tone plus text; never color alone.
- **Data table:** stable alignment, overflow strategy, empty state, and optional sorting/filtering/pagination.
- **Dialog:** labelled title, bounded scrollable body, clear close/cancel and confirm actions, focus management.
- **Long-text helper:** truncation only when needed with a usable full-value path.

## Inspected implementation examples

The demo implements `PageHeader` and `Panel` in `layout.jsx`; button/input/select/card/badge in `ui.jsx`; `Field` and `useFormCheck` in `Field.jsx`; `StatTile`; `Sidebar`; `Truncate`; shared `Pagination`; and Radix-backed `Modal` plus `ConfirmDialog`. It uses Radix for dialog/focus behavior rather than hand-rolling it. Reuse an equivalent component from the target project before adding another.
