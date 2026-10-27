---
name: Duck Debugger
colors:
  surface: '#0a122a'
  surface-dim: '#0a122a'
  surface-bright: '#313852'
  surface-container-lowest: '#050d25'
  surface-container-low: '#131a33'
  surface-container: '#171e37'
  surface-container-high: '#212942'
  surface-container-highest: '#2c344d'
  on-surface: '#dbe1ff'
  on-surface-variant: '#d0c2d5'
  inverse-surface: '#dbe1ff'
  inverse-on-surface: '#282f49'
  outline: '#998d9e'
  outline-variant: '#4d4353'
  surface-tint: '#e0b6ff'
  primary: '#e0b6ff'
  on-primary: '#4c007d'
  primary-container: '#9d4edd'
  on-primary-container: '#fffdff'
  inverse-primary: '#8433c4'
  secondary: '#deb7ff'
  on-secondary: '#4a007f'
  secondary-container: '#6b13af'
  on-secondary-container: '#d4a5ff'
  tertiary: '#e1b6ff'
  on-tertiary: '#4c007b'
  tertiary-container: '#9b53d2'
  on-tertiary-container: '#fffdff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#f2daff'
  primary-fixed-dim: '#e0b6ff'
  on-primary-fixed: '#2e004e'
  on-primary-fixed-variant: '#6a0baa'
  secondary-fixed: '#f1dbff'
  secondary-fixed-dim: '#deb7ff'
  on-secondary-fixed: '#2d0050'
  on-secondary-fixed-variant: '#680eac'
  tertiary-fixed: '#f2daff'
  tertiary-fixed-dim: '#e1b6ff'
  on-tertiary-fixed: '#2e004d'
  on-tertiary-fixed-variant: '#691a9f'
  background: '#0a122a'
  on-background: '#dbe1ff'
  surface-variant: '#2c344d'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  code-lg:
    fontFamily: JetBrains Mono
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 24px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-md: 1.5rem
  gutter-lg: 2rem
  margin: 1rem
  margin-md: 2rem
  margin-lg: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system targets software engineers, systems architects, and technical problem-solvers navigating complex logic breakdowns through guided inquiry. The brand personality is razor-sharp, analytical, focused, yet subtly playful—channeling the classic rubber duck debugging methodology into a high-performance terminal and studio environment. 

The aesthetic fuses modern developer tooling ergonomics with refined glassmorphism and technical brutalism: deep midnight navy voids, electric violet luminescence, crisp low-contrast borders, and high-legibility typographic hierarchies. It avoids frivolous decoration in favor of tactical feedback loops, syntax-level clarity, and focused conversational states that induce flow without visual fatigue.

## Colors
The color architecture relies on high-contrast dark space layering with luminous violet accents for state representation and interactive emphasis:

- **Canvas & Backgrounds**: Base background defaults to deep void `#0B132B`, stepping up to `#1C2541` for elevated workspace containers and panels.
- **Surfaces & Cards**: Elevated modules use dark navy slate `#151E3F` and `#1E293B`, reinforced with subtle linear gradients and border strokes. Crisp clean white (`#FFFFFF`, `#F8F9FA`) is reserved strictly for high-priority terminal text and prominent prompt tokens.
- **Primary & Interactive Accents**: Electric Purple (`#9D4EDD`) acts as the active trigger and interactive focus. Deep Violet (`#7B2CBF`) supports pressed or secondary-action hierarchies, while Lavender Violet (`#C77DFF`) handles inline highlights, focus rings, and glowing badges.
- **Borders & Dividers**: Sub-pixel structural seams utilize muted slate navies `#2A324B` (recessed/passive) and `#3A405A` (structural cards/inputs).
- **Luminescence & Glows**: Active code streams and conversational triggers leverage diffused neon purple glows (`rgba(157, 78, 221, 0.20)`).

## Typography
Typographic discipline pairs functional modern sans-serif typography (`Inter`) with an engineered monospace system (`JetBrains Mono`):

- **Inter**: Drives primary application UI, Socratic conversational prose, prompts, dialogs, and structural headlines. Tight negative letter spacing is applied to headings for an authoritative, precision-engineered feel.
- **JetBrains Mono**: Powers code snippets, logic expressions, stack traces, badge pills, metadata metrics, key-value inspector labels, and step counts.
- **Scale Dynamics**: Headlines scale down via strict responsive tokens on narrow screens to preserve layout continuity during intense multi-pane debugging sessions.

## Layout & Spacing
The layout follows a responsive 12-column fluid grid tailored for high-density developer workflows. It supports split-screen triage: inquiry stream on one side, context/code inspector on the other.

- **Desktop (1200px+)**: Multi-column pane layout with adjustable splitters, 32px (`gutter-lg`) gutters, and 48px (`margin-lg`) margin edges.
- **Tablet (768px - 1199px)**: Dual-pane collapsible drawer configuration with 24px (`gutter-md`) gutters and 32px (`margin-md`) canvas margins.
- **Mobile (<768px)**: Single-column vertical stream with bottom-sheet drawers for inspectable stack traces, using 16px (`gutter`) gutters and 16px (`margin`) boundary margins.
- **Component Rhythm**: Strict 4px/8px incremental rhythm for interior component padding (`space-xs` through `space-xl`) to establish predictable vertical scanning.

## Elevation & Depth
Depth is produced through translucent dark layering, luminous backdrops, and tight hairline borders rather than muddy black drop shadows:

- **Level 0 (Canvas)**: Solid `#0B132B` void.
- **Level 1 (Docked Containers & Split Panes)**: Background `#151E3F` at 85% opacity with a `16px` backdrop-blur and a `1px` border of `#2A324B`.
- **Level 2 (Cards & Floating Prompts)**: Background `#1E293B` at 90% opacity, `1px` border of `#3A405A`, and a subtle drop shadow `0 8px 32px -4px rgba(11, 19, 43, 0.8)`.
- **Level 3 (Focused Interactive Modals & Active Socratic Duck Cards)**: Background `#1E293B`, `1px` border of `rgba(199, 125, 255, 0.45)`, and an exterior accent aura `0 0 24px 0 rgba(157, 78, 221, 0.20)`.

## Shapes
The visual system centers around roundedness level `2`. Standard interactive elements, code blocks, and conversational cards use 12px to 16px corner radii to balance approachable guidance with sharp software architecture:

- **Standard Elements (Inputs, Buttons, Cards)**: Default to `rounded-lg` (16px / 1rem) for an ergonomic, modern look.
- **Small Controls (Badges, Tooltips, Checkboxes)**: Utilize `rounded` (8px / 0.5rem) to keep dense layouts structured.
- **Status Pills & Micro Chips**: Implement complete pill radius (`rounded-full`) for high-contrast tag isolation.

## Components

### Buttons
- **Primary**: Solid electric purple background (`#9D4EDD`) transitioning to `#7B2CBF` on hover, white text (`#FFFFFF`), `rounded-lg` (16px), subtle ambient glow (`0 0 16px rgba(157, 78, 221, 0.4)`).
- **Secondary / Ghost**: Transparent fill, `1px` border of `#3A405A`, text in `#C77DFF`. On hover: surface tints to `rgba(157, 78, 221, 0.1)` with border brightening to `#9D4EDD`.
- **Code Action**: Monospace labels (`JetBrains Mono`, `label-md`), compact height (32px), padded horizontally by `space-sm`.

### Tech Badges & Status Pills
- Pill-shaped (`rounded-full`), padded `space-xs` vertically and `space-sm` horizontally.
- Font: `JetBrains Mono` (`label-sm`).
- **Styles**: Monochromatic slate (`bg: #1C2541`, `text: #94A3B8`, `border: #2A324B`) or Active State (`bg: rgba(157, 78, 221, 0.15)`, `text: #C77DFF`, `border: rgba(199, 125, 255, 0.3)`).

### Cards & Socratic Message Modules
- Surface: `#1E293B` blended with `backdrop-filter: blur(12px)`.
- Border: `1px solid #3A405A`. Corner radius: `16px`.
- Duck Response variant: Features an inset left-border highlight in `#9D4EDD` (`3px`) with a soft glow `0 0 20px rgba(157, 78, 221, 0.12)`.

### Input Fields & Monospace Editors
- Input surface: `#151E3F` with an inset `1px` border of `#2A324B`.
- Text: `#F8F9FA` in `Inter` (prose query) or `JetBrains Mono` (code snippet input).
- Focus state: Border transitions to `#C77DFF` with an outer glow box-shadow `0 0 0 3px rgba(157, 78, 221, 0.25)`.

### Checkboxes & Toggle Controls
- Checkbox container: 18x18px, `rounded` (4px), border `1.5px solid #3A405A`, background `#151E3F`.
- Checked state: `#9D4EDD` background with a crisp white check icon and subtle violet halo.

### Specialized Studio Components
- **Syntax Highlighter Block**: Surface `#0B132B`, top titlebar in `#1C2541` housing filename, language badge pill, and copy button. Syntax palette utilizes electric violet, soft cyan, and amber against pure white tokens.
- **Thinking Prompt Breadcrumbs**: Interactive stepper indicating the Socratic resolution stage (e.g., `Hypothesis` → `Isolate` → `Explain` → `Synthesize`) with connected neon tracks.