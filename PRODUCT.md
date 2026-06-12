# Product

## Register

product

## Users

Primary users are:
- **FBR auditors / tax investigators** reviewing resolved taxpayer profiles for hidden assets and under-reporting.
- **Forensic financial investigators** tracing beneficial ownership and associate-linked risk across civic records.
- **Hackathon judges / demo visitors** who need to immediately understand what the system does and why a profile is flagged.

The interface is used on a laptop or large monitor in an office or demo setting. Users are domain-knowledgeable but not necessarily engineers; they need clarity over density.

## Product Purpose

TaxNet XAI links fragmented civic datasets (tax, property, vehicle, utility, offshore leaks, sanctions) into a single entity graph, scores every resolved profile for lifestyle-versus-income deviation, and explains each score with interpretable evidence.

The UI must make the audit pipeline transparent: show which records were linked, why an entity was flagged, what the graph relationships are, and how the score breaks down — without drowning the user in raw data.

## Brand Personality

Forensic, credible, clean.

The interface should feel like a trustworthy government investigation tool, not a fintech dashboard or a cyberpunk terminal. Precision, hierarchy, and calm authority are more important than visual excitement.

## Anti-references

- Dark neon / cyberpunk aesthetics.
- Generic Bootstrap/Material admin templates.
- Cluttered, spreadsheet-like density.
- Fintech jargon, crypto styling, or alarmist red-black security dashboards.
- Excessive gradients, glassmorphism, or decorative motion.

## Design Principles

1. **Evidence first.** Every flag must be accompanied by the records and reasoning that produced it.
2. **Calm authority.** Use restrained color, clear typography, and consistent spacing to convey trustworthiness.
3. **Progressive disclosure.** Surface the headline score and reasons immediately; let users drill into graph evidence, source rows, and SHAP explanations on demand.
4. **Interpretable over impressive.** Charts and graphs must answer audit questions, not decorate the page.
5. **Accessible by default.** Reduced motion, color-blind-safe palettes, and WCAG 2.1 AA contrast.

## Accessibility & Inclusion

- Target WCAG 2.1 AA contrast ratios.
- Respect `prefers-reduced-motion`; no layout-driven animation.
- Color-blind-safe data visualization: do not rely on hue alone for risk tiers; combine color with shape, pattern, and labels.
