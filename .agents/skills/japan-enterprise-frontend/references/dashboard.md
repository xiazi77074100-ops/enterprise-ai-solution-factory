# Dashboard

## Make it a work surface

Prioritize information that helps users decide or act: exceptions and risks, work due soon, progress, key totals, and the next useful destination. Order sections by urgency and workflow. A dashboard should answer “what needs attention?” before presenting decorative charts or a wall of equal-weight cards.

Use KPIs to summarize, not to duplicate full reports. Give each metric a clear period/scope, unit, and comparison where needed. Separate value and unit when that improves scanning. A number that opens a filtered list should look actionable and have a clear accessible name.

Charts need a title, units, labels/legend where useful, and an accessible textual summary or data alternative. Keep color mapping stable and distinguish status with text or symbols too.

## Cards and customization

Use consistent card headers and content padding. Make draggable or resizable affordances visible and constrain drag handles to areas that do not conflict with links or buttons inside the card. Save layout changes only after an actual user edit, and provide a way to restore defaults if customization is persistent.

Include loading, no-data, and error states that preserve the card's context. Avoid animating large values continuously; motion should communicate a real update and respect reduced-motion settings.

## Demo reference

The demo shares a 40px panel header and 34px KPI label band. KPI values use 18/24/28px by size, and its role-aware dashboard metrics can drill into filtered list views. Dashboard layout preferences are scoped to user and role. These are patterns found in `layout.jsx`, `StatTile.jsx`, `Dashboard.jsx`, and `widgets.jsx`, not a recommended default dashboard content set.
