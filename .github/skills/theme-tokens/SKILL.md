---
name: theme-tokens
description: Enforce theme-aware CSS tokens in UI views. Validates that EJS templates and inline styles use only design-system variables from style.css. Catches non-existent vars that break light or dark mode.
argument-hint: "[check|fix] - audit or fix CSS variable usage in UI views"
---

# Theme-Aware CSS Tokens

Ensure all UI views use only valid CSS custom properties from the design system (`services/ui-console/public/style.css`). Non-existent variables render as transparent/invisible, breaking light or dark mode.

## When to Use

- When creating or editing any EJS template in `services/ui-console/views/`
- When adding inline `style=""` attributes with `var(--*)` references
- When adding `<style>` blocks inside EJS templates
- During code review of UI changes
- After a user reports "invisible" or "unreadable" elements in light/dark mode

## Valid CSS Token Reference

### Backgrounds

| Token              | Light                    | Dark                      | Use for                           |
| ------------------ | ------------------------ | ------------------------- | --------------------------------- |
| `--bg`             | `#f8fafc`                | `#0b0f1a`                 | Page / modal background           |
| `--glass-bg`       | `rgba(255,255,255,0.72)` | `rgba(255,255,255,0.035)` | Cards, panels, surfaces           |
| `--glass-hover-bg` | `rgba(255,255,255,0.88)` | `rgba(255,255,255,0.065)` | Hovered cards/rows                |
| `--input-bg`       | `rgba(15,23,42,0.03)`    | `rgba(255,255,255,0.04)`  | Inputs, code blocks, result areas |
| `--input-focus-bg` | `rgba(255,255,255,0.9)`  | `rgba(255,255,255,0.06)`  | Focused input fields              |
| `--rail-bg`        | `rgba(248,250,252,0.92)` | `rgba(11,15,26,0.92)`     | Nav rail                          |
| `--topbar-bg`      | `rgba(248,250,252,0.88)` | `rgba(11,15,26,0.75)`     | Top bar                           |
| `--tooltip-bg`     | `#0f172a`                | `rgba(15,23,42,0.95)`     | Tooltips                          |
| `--badge-bg`       | `rgba(15,23,42,0.05)`    | `rgba(255,255,255,0.05)`  | Badges, tags                      |

### Borders

| Token                  | Use for              |
| ---------------------- | -------------------- |
| `--glass-border`       | Card/panel borders   |
| `--glass-hover-border` | Hovered card borders |
| `--input-border`       | Input field borders  |
| `--rail-border`        | Nav rail border      |
| `--topbar-border`      | Top bar border       |
| `--tooltip-border`     | Tooltip borders      |
| `--badge-border`       | Badge borders        |
| `--divider`            | Section dividers     |
| `--border-base`        | Generic base border  |

### Text Colors

| Token           | Use for                          |
| --------------- | -------------------------------- |
| `--text-1`      | Primary text, headings           |
| `--text-2`      | Secondary text, descriptions     |
| `--text-3`      | Muted text, labels, placeholders |
| `--text-4`      | Very muted, disabled text        |
| `--accent-text` | Accent-colored text (cyan)       |

### Shadows

| Token                  | Use for                  |
| ---------------------- | ------------------------ |
| `--glass-shadow`       | Default card shadow      |
| `--glass-hover-shadow` | Hovered card shadow      |
| `--glass-inset`        | Inset highlight on cards |
| `--tooltip-shadow`     | Tooltip shadow           |

### Status Colors

| Token                                             | Use for               |
| ------------------------------------------------- | --------------------- |
| `--accent` / `--accent-glow`                      | Primary accent (cyan) |
| `--success` / `--success-bg` / `--success-border` | Success states        |
| `--warn` / `--warn-bg` / `--warn-border`          | Warning states        |
| `--danger` / `--danger-bg` / `--danger-border`    | Error/danger states   |

### Misc

| Token                                     | Use for                  |
| ----------------------------------------- | ------------------------ |
| `--rail-hover-bg`                         | Hovered nav items        |
| `--dot-grid-color`                        | Background dot grid      |
| `--scrollbar-thumb` / `--scrollbar-hover` | Custom scrollbars        |
| `--selection-bg` / `--selection-color`    | Text selection           |
| `--btn-secondary-hover-bg`                | Secondary button hover   |
| `--btn-ghost-hover-bg`                    | Ghost button hover       |
| `--ring-inner` / `--ring-empty`           | Ring/progress indicators |
| `--delete-hover-bg`                       | Delete button hover      |

## Banned Variables (DO NOT USE)

These do **not** exist in the design system and will render as transparent:

| Banned        | Correct Replacement |
| ------------- | ------------------- |
| `--card-bg`   | `--glass-bg`        |
| `--surface-2` | `--input-bg`        |
| `--border`    | `--glass-border`    |
| `--bg-1`      | `--bg`              |
| `--bg-3`      | `--input-bg`        |

## Procedure

### 1. Audit — Find Non-Existent Variables

Search all EJS views for banned variable names:

```bash
grep -rn --include="*.ejs" "var(--card-bg)\|var(--surface-2)\|var(--border)\|var(--bg-1)\|var(--bg-3)" services/ui-console/views/
```

If matches are found, replace each with the correct token from the **Banned Variables** table above.

### 2. Verify — Check Against Design System

For any `var(--something)` in a view file, confirm `--something` exists in `style.css` under both `:root` and `.dark`. If it only exists in one, it will break the other mode.

### 3. Common Patterns

**Card/panel background:**

```css
background: var(--glass-bg);
border: 1px solid var(--glass-border);
```

**Input/code block background:**

```css
background: var(--input-bg);
border: 1px solid var(--input-border);
```

**Modal overlay:**

```css
background: var(--bg);
border: 1px solid var(--glass-border);
```

**Hover state:**

```css
background: var(--glass-hover-bg);
border-color: var(--glass-hover-border);
```

**Select/dropdown:**

```css
background: var(--input-bg);
color: var(--text-1);
border: 1px solid var(--input-border);
```

### 4. EJS Template Literal Rules

When writing styles inside EJS template literal body (`<%- include('layout', { ..., body: \`...\` }) %>`):

- Backtick characters **cannot** appear inside the body — use `String.fromCharCode(96)`
- `</script>` must be written as `<\/script>`
- All backslashes are consumed as escape chars — double them (`\\`)
- Closing line must be `` `}) %>`` with `}` to close the object literal
