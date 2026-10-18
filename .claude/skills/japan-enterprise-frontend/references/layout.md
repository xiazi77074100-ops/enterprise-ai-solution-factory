# Layout

## Shell and page structure

Treat the shell as persistent context: navigation, top-level header or tabs, current page, and main content. Navigation should show the current location through more than color alone. A collapsed sidebar still needs recognizable controls, accessible names, and tooltips for icon-only items.

For a dense list or detail page, use a flexible column layout with `min-height: 0` on the constrained flex child and put scrolling on the content region. This lets the shell stay fixed while the intended region scrolls. Keep a toolbar and pagination visible when they are needed throughout the task.

## Page header

Use one page-level heading in the document outline. A visible page title is useful when the content is a record name or the location is otherwise unclear. If the shell already makes the current screen unmistakable, retain a screen-reader heading and use the visible header row for scope, result count, notices, and primary actions.

Place actions at the end of the header row and let metadata wrap cleanly. Do not repeat the same explanation in both the header and a notice.

## Spacing and responsive behavior

- Choose a small spacing scale and use it consistently for page padding, section gaps, panel padding, and control gaps.
- Prefer responsive wrapping or grid changes over shrinking labels until unreadable.
- Dense tables may scroll horizontally inside their own region; keep the page shell from gaining accidental horizontal overflow.
- Keep modal content bounded by viewport height and scroll its body, not the whole application.

## Demo reference values

In the inspected demo, ordinary list pages use `p-4` with `gap-3`; the sidebar is 14rem when open and 60px when collapsed; page content uses flex/min-height constraints. `PageHeader` renders an 18px visible title only when requested. These describe one app's tested proportions, not a universal layout grid.
