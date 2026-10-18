# Typography

## Hierarchy

Define a limited hierarchy for page title, panel/section title, body and controls, supporting text, and exceptional metric values. Prefer weight, spacing, and alignment to a large number of font sizes. Japanese text often has a different visual density from Latin text, so inspect real labels and long values at the intended viewport width.

Use a Japanese-capable system font stack and provide sensible fallbacks. Use tabular numerals for amounts, dates, counts, and other values compared across rows. Keep line height comfortable for Japanese glyphs and avoid clipping ruby/diacritics if the product uses them.

## Demo reference scale

The inspected theme documents five levels and uses approximately:

| Role | Demo value |
|---|---:|
| Visible page title | 18px / bold |
| Panel title | 15px / semibold |
| Section title | 14px / semibold |
| Body and table content | 13px |
| Supporting text | 12px |
| Fine metadata | 11px |
| KPI value | 18px, 24px, or 28px by context |

The demo notes 12px as its supporting-text floor. Treat this as a useful dense-UI reference, not a substitute for accessibility testing or user research. Do not scale every label down to fit; shorten copy, wrap metadata, or adjust layout first.

## Alignment

- Left-align prose and labels; right-align comparable numeric columns.
- Keep dates and amounts in predictable formats and align digits consistently.
- Avoid excessive letter spacing in Japanese body copy; use it sparingly for compact navigation group labels if needed.
