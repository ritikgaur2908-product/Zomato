---
name: Culinary Concierge
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#5b403f'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f0f1f1'
  outline: '#8f6f6e'
  outline-variant: '#e4bebc'
  surface-tint: '#bb162c'
  primary: '#b7122a'
  on-primary: '#ffffff'
  primary-container: '#db313f'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb3b1'
  secondary: '#835500'
  on-secondary: '#ffffff'
  secondary-container: '#feae2c'
  on-secondary-container: '#6b4500'
  tertiary: '#565d5f'
  on-tertiary: '#ffffff'
  tertiary-container: '#6f7678'
  on-tertiary-container: '#f9fdff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#ffddb4'
  secondary-fixed-dim: '#ffb955'
  on-secondary-fixed: '#291800'
  on-secondary-fixed-variant: '#633f00'
  tertiary-fixed: '#dde4e6'
  tertiary-fixed-dim: '#c1c8ca'
  on-tertiary-fixed: '#161d1f'
  on-tertiary-fixed-variant: '#41484a'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  display-lg:
    fontFamily: DM Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: DM Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: DM Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  title-md:
    fontFamily: DM Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: DM Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: DM Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: DM Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1200px
  gutter: 16px
---

## Brand & Style
The brand personality of the design system is warm, efficient, and sophisticated—functioning as a knowledgeable local guide. It targets urban food enthusiasts who value both speed of discovery and the quality of recommendations.

The visual style is **Corporate / Modern** with a focus on high-utility and warmth. It prioritizes clarity through generous whitespace and a "human" touch via soft curves and a warm-tinted neutral palette. The UI should feel inviting rather than clinical, reflecting the vibrancy of urban dining culture while maintaining the precision of an AI-driven discovery tool.

## Colors
The palette is centered around a vibrant **Primary Red (#E23744)**, used strategically for high-intent actions and brand presence. 

- **Primary:** Used for CTAs, active states, and critical brand touchpoints.
- **Secondary (Amber):** Reserved for "Premium" or "AI-Verified" indicators, providing a warm contrast to the primary red.
- **Surface & Background:** The background uses a soft Off-white (#FAFAFA) to reduce eye strain, while containers use pure White (#FFFFFF) or a very light Warm Gray (#F0F0F0) to create subtle depth.
- **Functional:** Success, Warning, and Error states follow standard patterns but are slightly desaturated to fit the warm aesthetic.

## Typography
This design system utilizes **DM Sans** across all levels to maintain a contemporary and approachable feel. The hierarchy is intentionally steep to help users quickly differentiate between restaurant names and metadata.

- **Headlines:** Bold and tight-leading for restaurant names and section headers.
- **Body:** Standardized at 16px for readability, with a 14px variant for secondary metadata (address, price range).
- **Labels:** Uppercase tracking is applied to small labels (e.g., "OPEN NOW", "AI PICK") to ensure they are legible at small sizes without competing with body text.

## Layout & Spacing
The layout follows a **Fluid Grid** model based on an 8px rhythm. 

- **Mobile:** 4-column grid with 16px side margins and 16px gutters.
- **Desktop:** 12-column grid with a maximum container width of 1200px.
- **Rhythm:** Use `md` (16px) for internal card padding and `lg` (24px) for vertical section spacing. This ensures a breathable layout that handles dense information like menus and reviews without feeling cluttered.

## Elevation & Depth
Depth is achieved through **Ambient Shadows** and **Tonal Layers**. Instead of harsh black shadows, we use a softened shadow with a hint of the primary brand color in the umbra (low opacity) to maintain warmth.

- **Level 0 (Flat):** Used for the main background (#FAFAFA).
- **Level 1 (Surface):** White containers with a 1px border (#E0E0E0) or a very soft 4px blur shadow. Used for standard list items.
- **Level 2 (Elevated):** Cards with a 12px blur shadow (opacity 0.08). Used for featured restaurant cards.
- **Level 3 (Overlay):** Used for modals and bottom sheets, employing a 24px blur shadow and a backdrop blur of 8px on the layer below.

## Shapes
The shape language is predominantly **Rounded**, conveying friendliness and modern polish. 

- **Standard Components:** Buttons and input fields use a `0.5rem` (8px) radius.
- **Containers:** Restaurant cards and bottom sheets use `rounded-lg` (16px) to create a distinct, soft frame for food photography.
- **Interactive Elements:** Pills and tags use a full circular radius (pill-shaped) to distinguish them from actionable buttons.

## Components

### Buttons & Controls
- **Primary Button:** Solid #E23744 with white text. High-contrast, 16px padding.
- **Budget Toggles:** Segmented controls with a soft gray background and a white "sliding" surface for the active state.
- **Sliders:** Minimalist tracks with a large, easy-to-tap 24px diameter handle.

### Restaurant Cards
- **Structure:** Top-heavy with high-resolution photography (16:9 ratio).
- **AI Explanation Block:** A distinct sub-section at the bottom of the card with a soft peach background (#FFF5F0) and a subtle left-border accent in Primary Red. It uses `body-sm` typography to explain "Why you'll like this."

### Inputs
- **Searchable Selects:** Inputs that transform into a full-screen or dropdown list with an integrated search bar.
- **Location Markers:** Use a custom "pin" icon with a pulse effect for the user's current location, using the Primary Red color.

### Status Alerts
- **Info/Warning/Error:** Use "Ghost" styling—pale background tints with high-saturation borders and icons. For example, Errors use a light pink background with a bold #E23744 text/icon.