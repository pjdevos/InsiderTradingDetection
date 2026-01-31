**I want to change the dashboard design. Design a real-time monitoring dashboard in the style outlined below.** Include all pages that are currently part of the dashboard (Overview, Alert Feed, Suspicious Winners, Trade History, Wallet Analysis, Network Patterns, Statistics, Settings), even if they are not mentioned below.



Visual Style: **Neo-brutalist design**

\- Bold, stark geometric shapes with heavy black borders (3-5px)

\- High contrast flat colors with no gradients or shadows

\- **Raw, unpolished aesthetic** with visible grid structures

\- Asymmetric layouts with intentional "imperfections" and overlapping elements

\- Brutalist typography: Bold sans-serif headlines, monospace for data

\- **Exposed structural elements** (show the "scaffolding")



Color Palette:

\- Base: **Black** (#000000) backgrounds, **White** (#FFFFFF) text and cards

\- Accent hierarchy:

&nbsp; - **Red** (#FF0000): Alerts, suspicious activity, critical warnings

&nbsp; - **Yellow** (#FFFF00): Warnings, attention-required items

&nbsp; - **Blue** (#0000FF): Links, normal activity, informational

&nbsp; - **Orange** (#FF8800): Secondary warnings, moderate alerts

\- Use thick colored borders and blocks, not subtle highlights

\- Text should be high-contrast (black on white or white on black)



Dashboard Components:

0\. Hero Section / Introduction Panel (collapsible, shown on first visit or toggleable):

&nbsp;  - Prominent placement: Top of page, full-width container

&nbsp;  - Neo-brutalist design: Large bold headline, thick black border (5px), yellow background

&nbsp;  - Content structure:

&nbsp;    - Headline: "POLYMARKET INSIDER TRADING DETECTOR" (bold, 32-40px, black text)

&nbsp;    - Tagline: "Real-time surveillance of prediction market manipulation" (18-20px)

&nbsp;    - Brief description (16px, 2-3 sentences, max-width for readability):

&nbsp;      "This dashboard monitors Polymarket prediction markets in real-time to detect 

&nbsp;      suspicious trading patterns that may indicate insider trading. The system 

&nbsp;      analyzes volume spikes, timing anomalies, and trader behavior to flag markets 

&nbsp;      that warrant closer investigation." Risk scores calculated from volume spikes, timing patterns, and trader behavior

&nbsp;    - Action button: "GOT IT   START MONITORING" (thick bordered button, black bg, white text)

&nbsp;      or simple "?" close button in top-right corner

&nbsp;  - Visual style:

&nbsp;    - Yellow (#FFFF00) background with 5px solid black border

&nbsp;    - Black text on yellow for maximum readability

&nbsp;    - Optionally: small brutalist icon (?? chart symbol or ?? magnifying glass as ASCII/emoji)

&nbsp;    - Box shadow: none (flat design)

&nbsp;    - Padding: generous (40-60px on desktop, 20-30px on mobile)

&nbsp;  - Behavior:

&nbsp;    - Show automatically on first visit (check localStorage flag: "hasSeenIntro")

&nbsp;    - After dismissal, add "?? ABOUT" or "?" button in main header to re-open

&nbsp;    - Collapse with simple fade-out or slide-up animation (200-300ms)

&nbsp;    - On mobile: takes full viewport, scroll if needed

&nbsp;  - Accessibility:

&nbsp;    - Keyboard dismissible (ESC key or TAB to button)

&nbsp;    - Focus trap while open

&nbsp;    - aria-label="Introduction and dashboard guide"



1\. Header Bar (fixed top, after hero is dismissed):

&nbsp;  - App title with bold typography: "POLYMARKET MONITOR" (24-28px)

&nbsp;  - Real-time status indicator: "? LIVE" (green dot) or "? PAUSED" (gray)

&nbsp;  - Last update timestamp: "Updated: 14:32:18" (monospace font)

&nbsp;  - Quick filters (pill-style buttons with thick borders):

&nbsp;    - "ALL MARKETS" | "FLAGGED ONLY" | "HIGH RISK"

&nbsp;  - "?? ABOUT" button to reopen Hero Section

&nbsp;  - Background: White with black bottom border (3px)

&nbsp;  - Height: 60-80px

&nbsp;  - Sticky position on scroll



2\. Alert Stream (left sidebar, ~30% width):

&nbsp;  - Live feed of detected suspicious patterns

&nbsp;  - Color-coded by severity:

&nbsp;    - Red border (left, 10px): High risk

&nbsp;    - Orange border: Medium risk  

&nbsp;    - Yellow border: Low risk

&nbsp;  - Compact card design (each alert):

&nbsp;    - Market name (bold, 14px, truncated)

&nbsp;    - Trader ID (monospace, abbreviated: "Trader #A7F2...")

&nbsp;    - Pattern type (e.g., "Volume Spike +340%", "Timing Anomaly")

&nbsp;    - Timestamp (relative: "2m ago" or absolute: "14:30")

&nbsp;  - Styling:

&nbsp;    - White background cards

&nbsp;    - Black text

&nbsp;    - 3px black border + thick colored left border

&nbsp;    - 8-12px padding

&nbsp;    - 8px gap between cards

&nbsp;  - Behavior:

&nbsp;    - Sticky scroll, independent of main content

&nbsp;    - Most recent on top

&nbsp;    - Max height: viewport height minus header

&nbsp;    - Click to highlight corresponding market in main grid



3\. Market Overview Grid (main area, ~70% width):

&nbsp;  - CSS Grid layout: 2-3 columns depending on viewport width

&nbsp;  - Each market card shows:

&nbsp;    - Market question (bold, 16px, truncated with "..." after ~60 chars)

&nbsp;    - Current odds visualization: 

&nbsp;      - Large percentage (32px, monospace): "67%" 

&nbsp;      - Simple horizontal bar (thick, colored)

&nbsp;    - Risk score meter: 

&nbsp;      - "RISK: HIGH" / "MEDIUM" / "LOW" (12px, bold, colored text)

&nbsp;      - Colored horizontal bar (10px height, full width)

&nbsp;    - Volume spike indicator: "? +240%" (if applicable, colored)

&nbsp;    - Last unusual activity: "?? 15m ago" (small, monospace)

&nbsp;  - Card styling:

&nbsp;    - White background

&nbsp;    - 4px solid black border

&nbsp;    - Left border override: 10px colored border if alert exists (red/orange/yellow)

&nbsp;    - Padding: 20px

&nbsp;    - Hover state: Invert to black background, white text

&nbsp;    - Active/selected: Yellow background

&nbsp;  - Grid spacing: 16px gap between cards

&nbsp;  - Click behavior: Opens Detail Panel (modal overlay)



4\. Detail Panel (modal overlay, expandable):

&nbsp;  - Triggered when clicking a market card

&nbsp;  - Full-screen overlay or large centered modal (80% viewport width/height)

&nbsp;  - Background: Semi-transparent black (#000000CC) overlay

&nbsp;  - Panel styling:

&nbsp;    - White background

&nbsp;    - Thick black border (5px)

&nbsp;    - Padding: 40px

&nbsp;  - Content:

&nbsp;    - Close button: Large "?" in top-right (black, 32px, clickable area 44x44px)

&nbsp;    - Market question: Full text, bold, 24px

&nbsp;    - Current odds: Large display (48px) with colored bar

&nbsp;    - Risk assessment: Colored box with score and reasoning

&nbsp;    - Trading pattern visualization: 

&nbsp;      - Simple line chart or bar chart

&nbsp;      - Thick lines (3-4px)

&nbsp;      - Minimal axes, clear labels (monospace)

&nbsp;      - Grid lines visible but subtle

&nbsp;      - No animations

&nbsp;    - Flagged transactions table:

&nbsp;      - Monospace font

&nbsp;      - Headers: TRADER | AMOUNT | TIME | PATTERN

&nbsp;      - Rows with alternating backgrounds (white/light gray)

&nbsp;      - Color-coded severity column (colored cell backgrounds)

&nbsp;    - Volume history: Simple bar chart, last 24h

&nbsp;  - Behavior:

&nbsp;    - Keyboard accessible (ESC to close, TAB navigation)

&nbsp;    - Click outside to close

&nbsp;    - Focus trap while open

&nbsp;    - No scroll on body while modal open



5\. Metrics Bar (top secondary bar, below header or bottom fixed):

&nbsp;  - Horizontal strip, full width

&nbsp;  - Background: Black with white text

&nbsp;  - Height: 40-50px

&nbsp;  - Content (evenly spaced):

&nbsp;    - "MARKETS MONITORED: 1,247" (monospace)

&nbsp;    - "ACTIVE ALERTS: 23" (with red circular badge)

&nbsp;    - "FLAGGED TODAY: 8" (orange text)

&nbsp;    - "SYSTEM STATUS: ? OPERATIONAL" (green dot)

&nbsp;  - Optional: Scrolling ticker animation for real-time updates (brutalist style: instant jumps, no smooth scroll)



Data Visualization Style:

\- Simple, bold charts with thick lines (3-4px stroke)

\- Minimal axes: only essential labels

\- Labels in monospace font (10-12px)

\- Use accent colors sparingly for data points (red for alerts, blue for normal)

\- Grid lines: 1px solid #CCCCCC (subtle but visible)

\- No animations or smooth transitions (instant state changes)

\- Chart backgrounds: white or light gray (#F5F5F5)

\- Legend: simple boxes with thick borders, not circles



Interaction Patterns:

\- Hover states: 

&nbsp; - Cards: Invert colors (black background, white text)

&nbsp; - Buttons: Add thick colored border or invert

\- Active/selected states: 

&nbsp; - Solid colored background (yellow primary, red for alerts)

&nbsp; - Black text for contrast

\- Buttons: 

&nbsp; - Thick bordered rectangles (3-4px)

&nbsp; - High contrast (black on white or white on black)

&nbsp; - Minimum size: 44x44px for touch targets

&nbsp; - Text: uppercase, bold, 14-16px

\- Links: 

&nbsp; - Blue (#0000FF) color

&nbsp; - Underlined

&nbsp; - Hover: thicker underline (3px)

\- Loading states: 

&nbsp; - Simple text "LOADING..." (blinking or static)

&nbsp; - Or basic geometric spinner (rotating square/triangle)

&nbsp; - No smooth animations

\- Focus indicators:

&nbsp; - Thick colored outline (3px, blue or yellow)

&nbsp; - High visibility for keyboard navigation



Responsive Behavior:

\- Desktop (>1200px): 

&nbsp; - Full three-column layout (hero ? header ? metrics bar ? alert sidebar + market grid)

&nbsp; - Alert sidebar fixed width (~350-400px)

&nbsp; - Market grid: 3 columns

\- Tablet (768-1200px): 

&nbsp; - Hero section full width (if visible)

&nbsp; - Alert sidebar stacks horizontally above main grid (scrolling horizontal cards)

&nbsp; - Market grid: 2 columns

&nbsp; - Metrics bar remains horizontal

\- Mobile (<768px): 

&nbsp; - Single column layout

&nbsp; - Hero section: reduced padding, smaller fonts

&nbsp; - Alert section: collapsible accordion ("?? 5 ACTIVE ALERTS   TAP TO EXPAND")

&nbsp; - Market cards: full width, stacked

&nbsp; - Metrics bar: stacks vertically or scrolls horizontally

&nbsp; - Detail panel: full screen (100% width/height)



Technical Requirements:

\- Layout: CSS Grid for main structure, Flexbox for components

\- Design tokens: CSS custom properties for colors, spacing, typography

```css

&nbsp; :root {

&nbsp;   --color-black: #000000;

&nbsp;   --color-white: #FFFFFF;

&nbsp;   --color-red: #FF0000;

&nbsp;   --color-yellow: #FFFF00;

&nbsp;   --color-blue: #0000FF;

&nbsp;   --color-orange: #FF8800;

&nbsp;   --border-thick: 5px;

&nbsp;   --border-medium: 3px;

&nbsp;   --border-thin: 1px;

&nbsp;   --spacing-xs: 8px;

&nbsp;   --spacing-sm: 16px;

&nbsp;   --spacing-md: 24px;

&nbsp;   --spacing-lg: 40px;

&nbsp;   --font-heading: 'Arial Black', sans-serif;

&nbsp;   --font-mono: 'Courier New', monospace;

&nbsp; }

```

\- HTML: Semantic elements (`<header>`, `<aside>`, `<main>`, `<article>`, `<dialog>`)

\- Performance: 

&nbsp; - Lazy load market cards if >50 markets

&nbsp; - Virtual scrolling for alert feed if >100 alerts

&nbsp; - Debounce real-time updates (max 1 update per second)

\- State management: Consider localStorage for:

&nbsp; - Hero section dismissal flag

&nbsp; - User filter preferences

&nbsp; - Collapsed/expanded sections



Accessibility Considerations:

\- Color independence: All red/yellow/orange indicators must have:

&nbsp; - Text labels ("HIGH RISK", "MEDIUM", "LOW")

&nbsp; - Icons or patterns (not color-only)

&nbsp; - Shape differences (circle vs square vs triangle for severity)

\- Contrast: Minimum 4.5:1 ratio (black/white = 21:1, well above standard)

\- Focus indicators: 

&nbsp; - Thick colored outline (3px solid blue or yellow)

&nbsp; - Never remove outline

&nbsp; - Visible on all interactive elements

\- Keyboard navigation:

&nbsp; - Logical tab order

&nbsp; - All actions accessible via keyboard

&nbsp; - Modal focus traps (TAB cycles within modal)

&nbsp; - ESC key closes modals/overlays

\- Screen readers:

&nbsp; - ARIA labels for icon-only buttons

&nbsp; - Live regions for alert feed (`aria-live="polite"`)

&nbsp; - Status messages announced (`role="status"`)

&nbsp; - Table headers properly marked (`<th scope="col">`)

\- Motion: Respect `prefers-reduced-motion` (disable animations)



Implementation Priority:

1\. Hero Section + Header (onboarding flow)

2\. Market Grid with basic cards (core functionality)

3\. Alert Stream sidebar (real-time monitoring)

4\. Detail Panel modal (deep dive capability)

5\. Metrics Bar (system overview)

6\. Responsive adaptations

7\. Accessibility refinements

8\. Performance optimizations



**Create a functional prototype that demonstrates the layout structure, color system, and key interactive states. Prioritize clarity and immediate comprehension of alert severity over aesthetic refinement. The design should feel raw, direct, and unapologetically functional like industrial machinery rather than consumer software.**



You can use neo-brutalist (or neobrutalism) libraries and component collections that work with Tailwind CSS, but be aware that many classes conflict with Streamlit's React components:

https://retroui.dev/

https://www.neobrutalism.dev/

https://github.com/ekmas/neobrutalism-components

https://github.com/michaelsieminski/neobrutalism-vue





