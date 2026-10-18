# japan-enterprise-frontend

A reusable UI skill for Japanese enterprise web applications. It extracts design and interaction principles from a real React demo implementation while keeping product-specific names, records, and branding out of the reusable guidance.

## Contents

- `SKILL.md`: when to apply the skill, evidence-first workflow, and core principles.
- `references/`: practical notes for tokens, layout, type, tables, forms, dashboards, Japanese wording, components, and review.

## Use

Place this directory in the skill search path supported by your coding agent, or point the agent at `SKILL.md`. Before implementation, inspect the target app's own theme, CSS, layout, and shared components. Treat the numeric values in the references as examples measured from the source demo, not as fixed requirements.

## Source basis

The skill was derived from the source implementation in `src/versions/shadcn/`, especially `theme.css`, `layout.jsx`, `ui.jsx`, `Field.jsx`, `StatTile.jsx`, `Sidebar.jsx`, `Truncate.jsx`, `Pagination.jsx`, and representative list/dashboard screens. It documents patterns and tradeoffs rather than demo business content.
