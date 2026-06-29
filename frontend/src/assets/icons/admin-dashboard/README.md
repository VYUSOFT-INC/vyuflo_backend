# Admin Dashboard Icons

15 SVG icon files for the Admin Dashboard page.

## Where to save

Save these into your project at:

```
frontend/src/assets/icons/admin-dashboard/
```

So the full path becomes e.g. `frontend/src/assets/icons/admin-dashboard/stat-users.svg`.

## File map (which icon goes where)

| File                          | Used for                              | Section            |
| ----------------------------- | ------------------------------------- | ------------------ |
| `stat-users.svg`              | "Total Users" KPI                     | KPI Tiles          |
| `stat-cases.svg`              | "Active Cases" KPI                    | KPI Tiles          |
| `stat-visa-types.svg`         | "Visa Types" KPI                      | KPI Tiles          |
| `stat-doc-types.svg`          | "Document Types" KPI                  | KPI Tiles          |
| `stat-ai-accuracy.svg`        | "AI Accuracy" KPI                     | KPI Tiles          |
| `stat-pending.svg`            | "Pending Issues" KPI                  | KPI Tiles          |
| `trend-up.svg`                | "+12.5% this month" style trend       | KPI Trend          |
| `trend-check.svg`             | "Managed" style indicator             | KPI Trend          |
| `trend-dot.svg`               | "All configured" / "Requires attn"    | KPI Trend          |
| `tab-dashboard.svg`           | Dashboard tab                         | Tab Nav            |
| `tab-doc-rules.svg`           | Document Rules tab                    | Tab Nav            |
| `tab-doc-guides.svg`          | Document Guides tab                   | Tab Nav            |
| `tab-letter-templates.svg`    | Letter Templates tab                  | Tab Nav            |
| `tab-ai-extraction.svg`       | AI Extraction Rules tab               | Tab Nav            |
| `tab-emergency.svg`           | Emergency Controls tab                | Tab Nav            |

## How to use (3 ways)

### Option 1 — Quick `<img>` (works immediately)
```tsx
import iconUsers from '../../assets/icons/admin-dashboard/stat-users.svg';

<img src={iconUsers} className="h-5 w-5" alt="" />
```
⚠️ Note: with `<img>`, you can't change icon color via CSS. The SVG uses
`stroke="currentColor"` which falls back to black when used as an image source.
If you want white-on-blue (like the KPI tile), edit the SVG file and
hard-code `stroke="white"`.

### Option 2 — As React component via SVGR (best for color theming)
Vite supports importing SVGs as React components out of the box with the
`?react` query (or `vite-plugin-svgr`). Then `currentColor` follows your
text color class.

```tsx
import IconUsers from '../../assets/icons/admin-dashboard/stat-users.svg?react';

<IconUsers className="h-5 w-5 text-white" />   // text-white → white stroke
```

### Option 3 — Stick with lucide-react (current code does this)
Already works, no files needed. Future swap path documented in
`AdminDashboard.tsx` comments.

## Notes

- All SVGs follow the lucide-react design system (MIT licensed, free for any use)
- 24×24 viewBox, 2px stroke, rounded line caps/joins
- `stroke="currentColor"` → color follows CSS `color` / Tailwind `text-*` when used
  as React component (Option 2) or inline SVG
- For `<img>` use (Option 1), edit each SVG file to hardcode the color you need
