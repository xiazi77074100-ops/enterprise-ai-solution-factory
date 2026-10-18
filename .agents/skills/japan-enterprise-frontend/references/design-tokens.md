# Design tokens

## Start from semantic roles

Inspect the existing theme and map its tokens to roles before choosing colors:

| Role | Use |
|---|---|
| Canvas / background | App work area behind content |
| Surface / card | Readable content groups and controls |
| Foreground | Main text and icons |
| Muted foreground | Secondary labels and supporting information |
| Border / input | Separation and control outlines |
| Primary / ring | Main action, selected state, keyboard focus |
| Success / warning / danger | Outcome and attention states |

Prefer semantic variables over raw color literals. A theme should define light and dark values for the same roles where both modes are supported. Keep status colors distinct from role or brand colors, and do not use a status hue as ordinary body text when contrast is weak.

## Surface hierarchy

Create depth with a small number of surfaces: canvas, content surface, and (when justified) navigation surface. Borders and subtle shadows should clarify grouping, not simulate elevation everywhere. In the inspected demo, the light canvas is slightly darker than white cards, while the sidebar has its own surface token. Its shadow is lighter in light mode and largely replaced by an outline in dark mode.

## Demo reference values (not defaults)

The source `theme.css` uses OKLCH variables. Its light primary is `oklch(0.52 0.14 258)`, background `oklch(0.962 0.006 258)`, card white, foreground `oklch(0.21 0.02 260)`, and radius `0.5rem`. Dark mode redefines these semantic variables. Use these only when the target product's brand and contrast needs support them.

## Rules

- Define tokens by purpose, not by page or component names.
- Use a consistent border/radius scale; avoid a new radius for every card.
- Build soft status surfaces from status tokens while retaining readable status text and an icon/label.
- Check contrast for text, controls, focus rings, and status badges in every theme.
- Keep role-specific color systems localized. The demo's role colors are explicit deep/soft/ink values rather than interpolated brand tints; this avoids confusing role identity with status.
