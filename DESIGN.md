---
name: TaxNet XAI
description: An evidence-first audit dashboard for resolved taxpayer risk, graph relationships, and explainable scoring.
colors:
  royal-ink: "#1a2b4a"
  sage-green: "#3d6b52"
  parchment-gold: "#d4b876"
  amber-alert: "#c88a2a"
  sienna-signal: "#a64b2a"
  paper-bg: "#f7f5f0"
  paper-surface: "#fdfcf9"
  paper-surface-2: "#f0ece4"
  ink: "#1e1e24"
  ink-muted: "#5e5c58"
  rule-line: "#dcd6cc"
  success: "#3d6b52"
  danger: "#a64b2a"
  warning: "#c88a2a"
typography:
  display:
    fontFamily: "'Cormorant Garamond', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(2rem, 4vw, 3rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "'Cormorant Garamond', Georgia, 'Times New Roman', serif"
    fontSize: "clamp(1.5rem, 2.5vw, 2rem)"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.005em"
  title:
    fontFamily: "'Source Sans 3', 'Inter', ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "0"
  body:
    fontFamily: "'Source Sans 3', 'Inter', ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "0"
  label:
    fontFamily: "'Source Sans 3', 'Inter', ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.06em"
    textTransform: "uppercase"
  mono:
    fontFamily: "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: "0"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.royal-ink}"
    textColor: "{colors.paper-surface}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
  button-primary-hover:
    backgroundColor: "{colors.sage-green}"
    textColor: "{colors.paper-surface}"
  button-secondary:
    backgroundColor: "{colors.paper-surface}"
    textColor: "{colors.royal-ink}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
  button-secondary-hover:
    backgroundColor: "{colors.paper-surface-2}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  card:
    backgroundColor: "{colors.paper-surface}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
  chip:
    backgroundColor: "{colors.paper-surface-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "4px 8px"
---

# Design System: TaxNet XAI

## 1. Overview

**Creative North Star: "The Courtroom Map"**

TaxNet XAI is an evidence board for financial investigators. Every element on screen exists to answer one question: *why was this entity flagged?* The interface treats the audit trail like a courtroom exhibit — documents are linked, relationships are mapped, and each conclusion is supported by cited records.

The atmosphere is institutional but not bureaucratic. Light-mode paper surfaces, authoritative serif display type, and restrained color coding create the feel of a well-organized case file rather than a dashboard. Motion is minimal and functional; the design relies on hierarchy, spacing, and typographic contrast to guide attention.

**Key Characteristics:**
- Evidence-first layout: score, reasons, graph, and source rows are always visible together.
- Light-mode paper palette with green, gold, and regal blue as semantic accents.
- Authoritative serif headings paired with a clean sans body and monospace data.
- Flat surfaces with tonal layering; no decorative shadows.
- Reduced-motion by default; color-blind-safe risk encoding.

## 2. Colors

The palette is built around paper-like neutrals with four deliberate accent roles: credibility green, money gold, authority blue, and signal orange. Accents are used semantically, not decoratively.

### Primary
- **Royal Ink Blue** (`#1a2b4a`): Primary action backgrounds, active navigation, and headline accents. Used on primary buttons, selected table rows, and the brand mark. This is the authority color.

### Secondary
- **Sage Green** (`#3d6b52`): Positive indicators, low-risk tiers, successful pipeline steps, and verified evidence. Also used for the network graph's "resolved" or "low-risk" node state.

### Tertiary
- **Aged Parchment Gold** (`#d4b876`): Highlights, premium signals, and the "money" metaphor. Used sparingly for high-value asset callsouts, score badges, and graph accents. This color should occupy ≤10% of any screen.

### Signal
- **Amber Alert** (`#c88a2a`): Medium-risk tiers and attention flags.
- **Burnt Sienna Signal** (`#a64b2a`): High and critical risk, errors, and urgent anomalies.

### Neutral
- **Paper Background** (`#f7f5f0`): Page background. Warm, slightly desaturated, never pure white.
- **Paper Surface** (`#fdfcf9`): Card and panel backgrounds.
- **Paper Surface 2** (`#f0ece4`): Secondary surfaces, hover states, zebra-striping.
- **Ink** (`#1e1e24`): Primary text.
- **Ink Muted** (`#5e5c58`): Secondary text, labels, timestamps.
- **Rule Line** (`#dcd6cc`): Borders, dividers, table lines.

### Named Rules
**The One Voice Rule.** The Royal Ink Blue is the only accent used for primary actions and navigation. Reserve Sage Green for success states, Gold for value highlights, and Amber/Sienna for risk. Never use two accents for the same semantic purpose.

**The Paper-First Rule.** Backgrounds are always warm paper tones. Pure white (`#ffffff`) and pure black (`#000000`) are prohibited.

## 3. Typography

**Display & Headlines:** Cormorant Garamond, Georgia, Times New Roman fallback. A high-contrast transitional serif that reads as authoritative and institutional.

**Body & UI:** Source Sans 3, Inter fallback. Clean, open, and neutral; keeps dense audit data readable.

**Data & Labels:** JetBrains Mono for numeric values, entity IDs, and timestamps. Source Sans 3 uppercase for micro-labels.

### Hierarchy
- **Display** (600, clamp(2rem, 4vw, 3rem), 1.05): Page title and major section headers.
- **Headline** (600, clamp(1.5rem, 2.5vw, 2rem), 1.1): Panel titles and graph section headers.
- **Title** (700, 1.125rem, 1.25): Card headings, entity names, table column group labels.
- **Body** (400, 0.9375rem, 1.55): Descriptions, explanations, and source-row text. Max line length 70ch.
- **Label** (700, 0.75rem, 1.2, uppercase 0.06em): Field labels, tags, risk tiers, micro-captions.
- **Mono Data** (500, 0.8125rem, 1.45): Scores, IDs, currency values, dates.

### Named Rules
**The Two-Typeface Rule.** Only serif display and sans body/mono are used. No third display face, no decorative script, no weight-only hierarchy without size contrast.

## 4. Elevation

The system is flat. Depth is conveyed through tonal layering (`paper-bg` → `paper-surface` → `paper-surface-2`) and 1px `rule-line` borders, not shadows.

Shadows appear only as transient state feedback: a subtle, diffuse shadow on hover for interactive cards or focused inputs. There are no persistent floating cards or drop shadows on panels.

### Shadow Vocabulary
- **Focus / Hover** (`0 2px 8px oklch(0.3 0.01 230 / 0.08)`): Soft lift for buttons, cards, and table rows on interaction.

### Named Rules
**The Flat-By-Default Rule.** Surfaces sit at the same elevation unless a user interacts with them. No permanent elevation.

## 5. Components

Components are refined and restrained. Radius is modest (8px), padding is generous but not spacious, and borders are 1px `rule-line`.

### Buttons
- **Shape:** Rounded corners (`8px`), no full pill shape.
- **Primary:** Royal Ink Blue background, Paper Surface text, no border. Padding `10px 18px`.
- **Hover / Focus:** Background shifts to Sage Green; focus ring is a 2px Royal Ink outline offset 2px.
- **Secondary:** Paper Surface background, Royal Ink text, 1px Rule Line border.
- **Ghost:** Transparent background, Ink Muted text, no border; used for minor actions and filters.

### Chips / Tags
- **Style:** Paper Surface 2 background, Ink text, 1px Rule Line border, 4px radius.
- **Risk variants:** Chips inherit risk-tier colors via background tint, not solid fills: low uses a sage tint, medium uses amber tint, high/critical use sienna tint. Text remains Ink for readability.

### Cards / Panels
- **Corner Style:** `8px` radius.
- **Background:** Paper Surface.
- **Border:** 1px Rule Line on all sides.
- **Shadow Strategy:** None at rest; focus/hover shadow only.
- **Internal Padding:** `16px` default, `24px` for major panels.

### Inputs / Fields
- **Style:** 1px Rule Line border, Paper Surface background, `8px` radius.
- **Focus:** Border shifts to Royal Ink Blue, no glow.
- **Error:** Border shifts to Burnt Sienna Signal, with signal-tinted background.

### Navigation / Top Bar
- **Style:** Paper Surface background, 1px Rule Line bottom border.
- **Typography:** Display font for the product name, sans label style for actions.
- **Active state:** Royal Ink text for the current action or selected entity.

### Signature Component: Evidence Graph
- A D3.js force-directed graph where nodes represent people, assets, and associated entities.
- Selected node is highlighted with a Royal Ink ring and Parchment Gold fill accent.
- Edges use Rule Line for neutral links, Sage Green for verified links, Amber/Sienna for risk-associated links.
- Labels are Mono Data size; node size encodes score or asset value.

## 6. Do's and Don'ts

### Do:
- **Do** use the paper palette as the default surface layer.
- **Do** encode risk with both color and shape/label: use colored risk chips with explicit text like "Critical", "High", "Medium", "Low".
- **Do** use Royal Ink Blue for the primary action and active navigation.
- **Do** reserve Sage Green for success, verification, and low-risk states.
- **Do** use Parchment Gold sparingly for high-value asset callouts.
- **Do** respect `prefers-reduced-motion`; transitions should be instant or near-instant for layout, and opacity-only for loaded content.
- **Do** cap body copy at 70ch and keep metric cards scannable with generous whitespace.

### Don't:
- **Don't** use dark mode, neon accents, or purple gradients.
- **Don't** use generic Bootstrap/Material admin template patterns like identical card grids or hero-metric big-number blocks.
- **Don't** use gradient text or glassmorphism.
- **Don't** rely on color alone for risk tiers; color-blind users must be able to read the tier label.
- **Don't** use border-left colored stripes as list-item accents.
- **Don't** use decorative motion, bounce, or elastic easing.
- **Don't** clutter the screen with spreadsheet-like raw data; source rows live in a dedicated, collapsible section.
