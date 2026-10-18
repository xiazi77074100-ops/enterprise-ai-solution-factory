# Japanese enterprise UI

## Wording

- Use natural, direct Japanese. Prefer a concrete action and outcome over vague commands such as 「実行」 when a clearer verb exists.
- Keep labels short but specific. Use consistent terms for the same entity and state across navigation, filters, forms, and confirmations.
- Avoid unexplained technical abbreviations and machine-translated phrasing. Use honorifics only where they fit the product's business voice.
- Distinguish action labels from state labels: for example, a button describes what it will do, while a badge describes the current state.
- Confirm destructive actions with the affected object and consequence; state whether recovery is possible when that matters.

## Dates, numbers, and units

Choose locale and time zone intentionally for the product and user base. Use locale-aware formatting where appropriate; do not assume every Japanese application should use JPY or Asia/Tokyo if it serves multiple regions or currencies. Keep units visible and consistent, and avoid putting a unit into a number if it prevents alignment or parsing.

## Japanese text layout

Test long company/person names, mixed kana/kanji/Latin text, full-width punctuation, and narrow screens. Avoid awkward breaks in IDs, dates, or codes; allow prose to wrap. Tooltips and accessible names should contain the full label when visible text is abbreviated.

## Demo reference

The inspected demo uses natural Japanese action wording, explicit units such as 件/社/人, and separates amount values from units in KPI tiles. Those choices provide examples; localization must follow the actual product's users and conventions.
