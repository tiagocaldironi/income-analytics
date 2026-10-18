# Breakpoints and responsive rules

The stylesheet already used feature-specific breakpoints at 900, 760, 720, 680, 520 px and below. Mobile UX V1 adds one shared shell threshold at **767 px**, matching the spec's mobile/desktop split; short landscape screens (height ≤480 px) also use the mobile shell so the top navigation cannot consume the viewport. A narrow-header adjustment at 375–390 px prevents the action button from widening the document; the existing ≤374 px adjustment remains.

Mobile spacing, safe-area and target-size tokens are centralized in `:root`: `--mobile-page-padding`, `--mobile-header-height`, `--mobile-bottom-nav-height`, `--touch-target-min` and `--mobile-card-gap`. Desktop selectors/layout remain the default and the mobile rules are additive. Historical feature breakpoints remain for existing component-specific adaptations and were not globally rewritten.

Mobile shell uses `env(safe-area-inset-top)` and `env(safe-area-inset-bottom)`. The body and main content reserve bottom navigation space. All viewport checks reported document width equal to viewport width.
