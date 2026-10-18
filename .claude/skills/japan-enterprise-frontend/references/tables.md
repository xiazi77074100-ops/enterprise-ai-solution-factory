# Tables

## Structure and scanning

Use semantic table markup with a header row and clear column labels. Keep headers on one line where possible; determine column widths from the data and truncate long cell values intentionally. Right-align numeric values, keep textual columns left-aligned, and use tabular numerals for comparison.

Use restrained row separators or subtle alternating row surfaces to help readers track across dense rows. Hover treatment should clarify an actual row action; do not imply clickability if the row is static. If a row is interactive, provide keyboard access and a visible focus state.

## Long values and overflow

Give columns deliberate widths or max widths and truncate within the cell. Make the full value available through a robust disclosure such as an accessible detail view or tooltip; do not rely on clipping alone. A tooltip should appear only when text is actually clipped and must not be the sole way to access essential information.

Keep the table in a scroll container when it cannot fit. Sticky headers and first columns can help, but test stacking, backgrounds, and focus at narrow widths. Use an empty row/state that explains why there are no results, and distinguish no matching results from no data when that distinction matters.

## Filtering and pagination

Group search and filters near the table. Make active filters visible and provide an obvious way to clear them. Preserve relevant incoming filter context when users navigate from a dashboard, and make that context removable.

Show result count, current range, and page controls with accessible labels. When filters change, reset or clamp the page index so users do not land on a now-empty page.

## Demo reference

The demo uses 13px table content, 12px headers, 8–12px cell padding, sticky headers, subtle striping, `Truncate` for long values, and a shared pagination component. Its `CustomerList.jsx` also demonstrates a sticky first column. Adopt these only when they fit the target data and screen.
