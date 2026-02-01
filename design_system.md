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

---

# IMPLEMENTATION PLAN

## Phase 1: Foundation & Core Infrastructure

### 1.1 Design System Setup
- Create CSS file with design tokens (colors, typography, spacing, borders)
- Set up base styles and CSS reset
- Configure responsive breakpoints
- Implement CSS Grid and Flexbox utilities

### 1.2 Layout Structure
- Build main app container with CSS Grid
- Implement responsive layout switching (desktop 3-column, tablet 2-column, mobile single)
- Set up sticky header positioning
- Configure scrollable regions (alert sidebar, main content)

## Phase 2: Core Components

### 2.1 Hero Section / Introduction Panel
- Full-width banner with yellow background
- Bold headline typography
- Collapsible behavior with localStorage integration
- "GOT IT" button or close "×" button
- Accessibility: focus trap, ESC key handler, ARIA labels

### 2.2 Header Bar
- Fixed top navigation (sticky position)
- App title with bold typography
- Live status indicator with colored dot
- Timestamp display (monospace)
- Quick filter pills (ALL MARKETS | FLAGGED ONLY | HIGH RISK)
- "ABOUT" button to reopen hero section

### 2.3 Metrics Bar
- Black background strip with white text
- Monospace statistics display
- Colored badges for active alerts
- Status indicator with icon

## Phase 3: Main Dashboard Components

### 3.1 Alert Stream Sidebar
- Fixed width scrollable container (~350-400px)
- Alert card component with:
  - Color-coded left border (10px thick: red/orange/yellow)
  - Market name (truncated)
  - Trader ID (monospace, abbreviated)
  - Pattern type label
  - Relative/absolute timestamp
- Sticky scroll behavior independent of main content
- Click handler to highlight corresponding market

### 3.2 Market Overview Grid
- CSS Grid with 2-3 columns (responsive)
- Market card component with:
  - Market question (bold, truncated)
  - Current odds visualization (large percentage + horizontal bar)
  - Risk score meter (colored bar + text label)
  - Volume spike indicator
  - Last unusual activity timestamp
- Card styling: white background, thick black border, colored left border override
- Hover state: inverted colors (black bg, white text)
- Active state: yellow background

## Phase 4: Advanced Components

### 4.1 Detail Panel Modal
- Full-screen overlay (semi-transparent black background)
- Large centered modal (80% viewport, white background, 5px black border)
- Close button (large "×" in top-right)
- Content sections:
  - Full market question (24px bold)
  - Large odds display (48px)
  - Risk assessment box (colored)
  - Trading pattern chart (thick lines, minimal axes)
  - Flagged transactions table (monospace, alternating rows)
  - Volume history bar chart
- Behavior: ESC to close, click outside to close, focus trap, prevent body scroll

### 4.2 Data Visualization Components
- Line chart component (3-4px thick lines, minimal axes, monospace labels)
- Bar chart component (thick bars, colored fills)
- Horizontal progress bar (risk meter)
- Simple geometric spinner/loader

## Phase 5: Additional Pages

### 5.1 Suspicious Winners Page
- Table layout with monospace font
- Sortable columns (trader, profit, timing score, market)
- Color-coded severity indicators
- Card view alternative for mobile

### 5.2 Trade History Page
- Timeline/chronological view
- Transaction cards with thick borders
- Filter controls (date range, trader, market)
- Pagination or infinite scroll

### 5.3 Wallet Analysis Page
- Wallet profile header
- Transaction history table
- Risk score visualization
- Network connection graph (simple nodes and edges)

### 5.4 Network Patterns Page
- Network graph visualization (simplified, brutalist style)
- Node legend (shape/color coding)
- Connection strength indicators
- Filter controls

### 5.5 Statistics Page
- Dashboard-style layout with stat cards
- Time-series charts for trends
- Distribution charts (histograms)
- Summary metrics grid

### 5.6 Settings Page
- Form controls with thick borders
- Toggle switches (brutalist style)
- Threshold sliders
- Notification preferences
- Data export options

## Phase 6: Responsive & Accessibility

### 6.1 Responsive Breakpoints
- Desktop (>1200px): Full layout
- Tablet (768-1200px): Stacked alert sidebar, 2-column grid
- Mobile (<768px): Single column, collapsible alerts

### 6.2 Accessibility Enhancements
- Focus indicators on all interactive elements (3px thick outline)
- ARIA labels for icon-only buttons
- Live regions for alert feed
- Keyboard navigation (TAB order, ESC handlers)
- Screen reader announcements
- Color-independent indicators (text labels + icons)
- `prefers-reduced-motion` support

---

# COMPONENT LIST

## Core Layout Components
1. **AppContainer** - Main grid layout wrapper
2. **AppHeader** - Sticky header with title, status, filters
3. **MetricsBar** - Statistics bar (black background)
4. **AppMain** - Main content grid (sidebar + content area)

## Hero/Onboarding Components
5. **HeroSection** - Introduction panel (yellow, dismissible)
6. **HeroClose** - Close button (× icon)
7. **AboutButton** - Button to reopen hero section

## Navigation Components
8. **HeaderTitle** - App logo/title
9. **StatusIndicator** - Live/paused indicator with colored dot
10. **Timestamp** - Last update timestamp
11. **FilterPills** - Quick filter buttons (ALL | FLAGGED | HIGH RISK)

## Alert Components
12. **AlertSidebar** - Scrollable alert feed container
13. **AlertCard** - Individual alert card with color-coded border
14. **SeverityBadge** - Colored label (CRITICAL, HIGH, MEDIUM, LOW)

## Market Components
15. **MarketGrid** - CSS grid container for market cards
16. **MarketCard** - Individual market card (clickable, hoverable)
17. **MarketQuestion** - Market title/question (truncated)
18. **MarketOdds** - Large percentage display with bar
19. **MarketRiskMeter** - Risk score with colored progress bar
20. **VolumeIndicator** - Spike indicator with percentage
21. **ActivityTimestamp** - Last unusual activity time

## Modal Components
22. **ModalBackdrop** - Semi-transparent overlay
23. **ModalPanel** - Main modal container
24. **ModalClose** - Close button (× icon)
25. **ModalSection** - Content section within modal

## Data Visualization Components
26. **ChartContainer** - Chart wrapper with border and padding
27. **LineChart** - Simple line chart (thick lines, minimal axes)
28. **BarChart** - Horizontal/vertical bar chart
29. **ProgressBar** - Horizontal progress bar (risk meters, odds)
30. **ChartLegend** - Legend with square boxes

## Table Components
31. **DataTable** - Transaction/trade history table
32. **TableHeader** - Black background header row
33. **TableRow** - Alternating white/gray rows
34. **TableCell** - Monospace data cells

## Form Components
35. **FormGroup** - Input wrapper with label
36. **TextInput** - Text/email/number input fields
37. **ToggleSwitch** - Brutalist checkbox toggle
38. **RangeSlider** - Brutalist range input
39. **Button** - Primary action button
40. **ButtonPill** - Small pill-shaped button

## Page-Specific Components

**Suspicious Winners Page**
- WinnersTable - Sortable trader table
- WinnerCard - Mobile card view for winners

**Trade History Page**
- TradeTimeline - Chronological transaction view
- TradeCard - Individual trade card
- DateRangeFilter - Date range selector

**Wallet Analysis Page**
- WalletProfile - Wallet header/summary
- TransactionHistory - Wallet transaction list

**Statistics Page**
- StatCard - Individual statistic card
- StatsGrid - Grid layout for stat cards
- TrendChart - Time-series chart

**Settings Page**
- SettingsSection - Grouped settings container
- ThresholdControl - Slider with value display
- NotificationToggle - On/off preference

## Utility Components
- LoadingSpinner - Geometric rotating spinner
- Badge - Colored numeric badge
- StatusDot - Colored circle indicator

---

# CSS STYLESHEET

```css
/* ============================================
   POLYMARKET INSIDER TRADING DETECTOR
   Neo-Brutalist Design System
   ============================================ */

/* ============================================
   CSS CUSTOM PROPERTIES (DESIGN TOKENS)
   ============================================ */

:root {
  /* Colors - Base */
  --color-black: #000000;
  --color-white: #FFFFFF;
  --color-gray-light: #F5F5F5;
  --color-gray-medium: #CCCCCC;
  --color-gray-dark: #666666;

  /* Colors - Accent */
  --color-red: #FF0000;
  --color-yellow: #FFFF00;
  --color-blue: #0000FF;
  --color-orange: #FF8800;
  --color-green: #00FF00;

  /* Colors - Severity */
  --color-critical: var(--color-red);
  --color-suspicious: var(--color-orange);
  --color-watch: var(--color-yellow);
  --color-normal: var(--color-blue);

  /* Borders */
  --border-thick: 5px;
  --border-medium: 4px;
  --border-normal: 3px;
  --border-thin: 2px;
  --border-hairline: 1px;

  /* Border Styles */
  --border-style-thick: var(--border-thick) solid var(--color-black);
  --border-style-medium: var(--border-medium) solid var(--color-black);
  --border-style-normal: var(--border-normal) solid var(--color-black);
  --border-style-thin: var(--border-thin) solid var(--color-black);

  /* Spacing */
  --spacing-xs: 8px;
  --spacing-sm: 12px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 40px;
  --spacing-xxl: 60px;

  /* Typography - Families */
  --font-heading: 'Arial Black', 'Arial Bold', Gadget, sans-serif;
  --font-body: Arial, Helvetica, sans-serif;
  --font-mono: 'Courier New', Courier, monospace;

  /* Typography - Sizes */
  --font-size-xs: 10px;
  --font-size-sm: 12px;
  --font-size-base: 14px;
  --font-size-md: 16px;
  --font-size-lg: 18px;
  --font-size-xl: 24px;
  --font-size-xxl: 32px;
  --font-size-xxxl: 48px;

  /* Typography - Weights */
  --font-weight-normal: 400;
  --font-weight-bold: 700;
  --font-weight-black: 900;

  /* Line Heights */
  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;

  /* Layout */
  --header-height: 80px;
  --metrics-bar-height: 50px;
  --sidebar-width: 380px;
  --max-content-width: 1920px;

  /* Touch Targets */
  --touch-target-min: 44px;

  /* Focus */
  --focus-outline: var(--border-normal) solid var(--color-blue);
  --focus-outline-offset: 2px;

  /* Z-index layers */
  --z-base: 1;
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-modal-backdrop: 900;
  --z-modal: 1000;
}

/* ============================================
   BASE STYLES & RESET
   ============================================ */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}

body {
  font-family: var(--font-body);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
  color: var(--color-black);
  background-color: var(--color-gray-light);
  overflow-x: hidden;
}

body.modal-open {
  overflow: hidden;
}

/* ============================================
   TYPOGRAPHY
   ============================================ */

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-heading);
  font-weight: var(--font-weight-black);
  line-height: var(--line-height-tight);
  margin: 0;
  text-transform: uppercase;
}

h1 { font-size: var(--font-size-xxxl); }
h2 { font-size: var(--font-size-xxl); }
h3 { font-size: var(--font-size-xl); }
h4 { font-size: var(--font-size-lg); }
h5, h6 { font-size: var(--font-size-md); }

.text-mono { font-family: var(--font-mono); }
.text-bold { font-weight: var(--font-weight-bold); }
.text-uppercase { text-transform: uppercase; }

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ============================================
   LINKS
   ============================================ */

a {
  color: var(--color-blue);
  text-decoration: underline;
  text-decoration-thickness: var(--border-hairline);
}

a:hover {
  text-decoration-thickness: var(--border-normal);
}

a:focus-visible {
  outline: var(--focus-outline);
  outline-offset: var(--focus-outline-offset);
}

/* ============================================
   BUTTONS
   ============================================ */

.btn {
  display: inline-block;
  font-family: var(--font-heading);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  text-decoration: none;
  text-align: center;
  padding: var(--spacing-sm) var(--spacing-lg);
  min-height: var(--touch-target-min);
  min-width: var(--touch-target-min);
  border: var(--border-style-normal);
  background-color: var(--color-white);
  color: var(--color-black);
  cursor: pointer;
  transition: none;
}

.btn:hover {
  background-color: var(--color-black);
  color: var(--color-white);
}

.btn:active {
  background-color: var(--color-yellow);
  color: var(--color-black);
}

.btn:focus-visible {
  outline: var(--focus-outline);
  outline-offset: var(--focus-outline-offset);
}

.btn-primary {
  background-color: var(--color-black);
  color: var(--color-white);
}

.btn-primary:hover {
  background-color: var(--color-white);
  color: var(--color-black);
}

.btn-danger {
  background-color: var(--color-red);
  color: var(--color-white);
}

.btn-pill {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  border-width: var(--border-thin);
}

/* ============================================
   CARDS
   ============================================ */

.card {
  background-color: var(--color-white);
  border: var(--border-style-medium);
  padding: var(--spacing-lg);
  position: relative;
}

.card-compact {
  padding: var(--spacing-sm);
}

.card-hover {
  cursor: pointer;
}

.card-hover:hover {
  background-color: var(--color-black);
  color: var(--color-white);
}

.card-active {
  background-color: var(--color-yellow);
  color: var(--color-black);
}

.card-border-left {
  border-left-width: 10px;
}

.card-border-critical { border-left-color: var(--color-critical); }
.card-border-suspicious { border-left-color: var(--color-suspicious); }
.card-border-watch { border-left-color: var(--color-watch); }

/* ============================================
   ALERTS & SEVERITY INDICATORS
   ============================================ */

.alert {
  padding: var(--spacing-md);
  border: var(--border-style-normal);
  margin-bottom: var(--spacing-md);
  background-color: var(--color-white);
}

.alert-critical { border-left: 10px solid var(--color-critical); }
.alert-suspicious { border-left: 10px solid var(--color-suspicious); }
.alert-watch { border-left: 10px solid var(--color-watch); }

.severity-badge {
  display: inline-block;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-family: var(--font-heading);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  border: var(--border-style-thin);
}

.severity-critical {
  background-color: var(--color-critical);
  color: var(--color-white);
}

.severity-high {
  background-color: var(--color-orange);
  color: var(--color-black);
}

.severity-medium {
  background-color: var(--color-yellow);
  color: var(--color-black);
}

.severity-low {
  background-color: var(--color-blue);
  color: var(--color-white);
}

/* ============================================
   TABLES
   ============================================ */

table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}

thead {
  background-color: var(--color-black);
  color: var(--color-white);
}

th {
  font-family: var(--font-heading);
  font-weight: var(--font-weight-bold);
  text-align: left;
  padding: var(--spacing-sm);
  border: var(--border-style-thin);
  text-transform: uppercase;
}

td {
  padding: var(--spacing-sm);
  border: var(--border-style-hairline);
}

tbody tr:nth-child(odd) { background-color: var(--color-white); }
tbody tr:nth-child(even) { background-color: var(--color-gray-light); }
tbody tr:hover { background-color: var(--color-yellow); }

/* ============================================
   LAYOUT - MAIN STRUCTURE
   ============================================ */

.app-container {
  display: grid;
  grid-template-rows: auto auto 1fr;
  grid-template-columns: 1fr;
  min-height: 100vh;
  max-width: var(--max-content-width);
  margin: 0 auto;
}

.app-header {
  grid-column: 1 / -1;
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  background-color: var(--color-white);
  border-bottom: var(--border-style-normal);
  padding: var(--spacing-md) var(--spacing-lg);
  min-height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-lg);
}

.app-metrics-bar {
  grid-column: 1 / -1;
  background-color: var(--color-black);
  color: var(--color-white);
  padding: var(--spacing-sm) var(--spacing-lg);
  min-height: var(--metrics-bar-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-lg);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}

.app-main {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  gap: 0;
  min-height: calc(100vh - var(--header-height) - var(--metrics-bar-height));
}

/* ============================================
   HERO SECTION
   ============================================ */

.hero-section {
  grid-column: 1 / -1;
  background-color: var(--color-yellow);
  border: var(--border-style-thick);
  padding: var(--spacing-xxl);
  text-align: center;
  position: relative;
}

.hero-section.hidden { display: none; }

.hero-headline {
  font-size: var(--font-size-xxxl);
  margin-bottom: var(--spacing-md);
  color: var(--color-black);
}

.hero-tagline {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-lg);
}

.hero-description {
  font-size: var(--font-size-md);
  max-width: 800px;
  margin: 0 auto var(--spacing-xl) auto;
  line-height: var(--line-height-relaxed);
}

.hero-close {
  position: absolute;
  top: var(--spacing-md);
  right: var(--spacing-md);
  font-size: var(--font-size-xxl);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs);
  min-width: var(--touch-target-min);
  min-height: var(--touch-target-min);
}

.hero-close:hover {
  background-color: var(--color-black);
  color: var(--color-white);
}

/* ============================================
   HEADER BAR
   ============================================ */

.header-title {
  font-family: var(--font-heading);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-black);
  text-transform: uppercase;
}

.header-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
}

.status-indicator {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: var(--border-thin) solid var(--color-black);
}

.status-live { background-color: var(--color-green); }
.status-paused { background-color: var(--color-gray-medium); }

.header-filters {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

/* ============================================
   METRICS BAR
   ============================================ */

.metric-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.metric-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 var(--spacing-xs);
  background-color: var(--color-red);
  color: var(--color-white);
  border-radius: 50%;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.metric-text-orange { color: var(--color-orange); }
.metric-text-green { color: var(--color-green); }

/* ============================================
   ALERT STREAM SIDEBAR
   ============================================ */

.alert-sidebar {
  background-color: var(--color-white);
  border-right: var(--border-style-normal);
  overflow-y: auto;
  padding: var(--spacing-md);
  max-height: calc(100vh - var(--header-height) - var(--metrics-bar-height));
  position: sticky;
  top: calc(var(--header-height) + var(--metrics-bar-height));
}

.alert-card {
  background-color: var(--color-white);
  border: var(--border-style-normal);
  border-left-width: 10px;
  padding: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
  cursor: pointer;
}

.alert-card:hover { background-color: var(--color-gray-light); }

.alert-card-market {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-base);
  margin-bottom: var(--spacing-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-card-trader {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-gray-dark);
  margin-bottom: var(--spacing-xs);
}

.alert-card-pattern {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-xs);
}

.alert-card-timestamp {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--color-gray-dark);
}

/* ============================================
   MARKET OVERVIEW GRID
   ============================================ */

.market-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background-color: var(--color-gray-light);
}

.market-card {
  background-color: var(--color-white);
  border: var(--border-style-medium);
  padding: var(--spacing-lg);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.market-card.has-alert { border-left-width: 10px; }

.market-card:hover {
  background-color: var(--color-black);
  color: var(--color-white);
}

.market-card.active {
  background-color: var(--color-yellow);
  color: var(--color-black);
}

.market-question {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-md);
  line-height: var(--line-height-tight);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.market-percentage {
  font-family: var(--font-mono);
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

.market-risk-label {
  font-family: var(--font-heading);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
}

/* ============================================
   PROGRESS BARS / RISK METERS
   ============================================ */

.progress-bar {
  width: 100%;
  height: 10px;
  background-color: var(--color-gray-light);
  border: var(--border-style-hairline);
  position: relative;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--color-blue);
}

.progress-bar-fill.critical { background-color: var(--color-critical); }
.progress-bar-fill.suspicious { background-color: var(--color-suspicious); }
.progress-bar-fill.watch { background-color: var(--color-watch); }

.progress-bar-thick { height: 20px; }

/* ============================================
   DETAIL PANEL / MODAL
   ============================================ */

.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-backdrop);
  padding: var(--spacing-lg);
}

.modal-backdrop.hidden { display: none; }

.modal-panel {
  background-color: var(--color-white);
  border: var(--border-style-thick);
  padding: var(--spacing-xl);
  max-width: 1200px;
  max-height: 90vh;
  width: 80%;
  overflow-y: auto;
  position: relative;
  z-index: var(--z-modal);
}

.modal-close {
  position: absolute;
  top: var(--spacing-md);
  right: var(--spacing-md);
  font-size: var(--font-size-xxl);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs);
  min-width: var(--touch-target-min);
  min-height: var(--touch-target-min);
  font-weight: var(--font-weight-bold);
}

.modal-close:hover {
  background-color: var(--color-black);
  color: var(--color-white);
}

.modal-title {
  font-size: var(--font-size-xl);
  margin-bottom: var(--spacing-lg);
  padding-right: var(--spacing-xxl);
}

.modal-odds-display {
  font-family: var(--font-mono);
  font-size: var(--font-size-xxxl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-md);
}

.modal-risk-box {
  padding: var(--spacing-lg);
  border: var(--border-style-medium);
  margin-bottom: var(--spacing-lg);
}

.modal-risk-box.critical {
  background-color: var(--color-critical);
  color: var(--color-white);
}

.modal-risk-box.suspicious {
  background-color: var(--color-suspicious);
  color: var(--color-black);
}

.modal-risk-box.watch {
  background-color: var(--color-yellow);
  color: var(--color-black);
}

/* ============================================
   CHARTS
   ============================================ */

.chart-container {
  background-color: var(--color-white);
  border: var(--border-style-normal);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.chart-title {
  font-family: var(--font-heading);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-md);
  text-transform: uppercase;
}

.chart-canvas {
  width: 100%;
  height: 300px;
  background-color: var(--color-gray-light);
  border: var(--border-style-hairline);
}

.chart-legend {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  margin-top: var(--spacing-md);
}

.chart-legend-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
}

.chart-legend-box {
  width: 20px;
  height: 20px;
  border: var(--border-style-thin);
}

/* ============================================
   LOADING STATES
   ============================================ */

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  font-family: var(--font-heading);
  font-size: var(--font-size-lg);
  text-transform: uppercase;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: var(--border-style-medium);
  border-top-color: var(--color-red);
  border-right-color: var(--color-yellow);
  border-bottom-color: var(--color-blue);
  border-left-color: var(--color-orange);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .loading-spinner {
    animation: none;
    border-color: var(--color-black);
  }
}

/* ============================================
   FORM ELEMENTS
   ============================================ */

input[type="text"],
input[type="email"],
input[type="number"],
textarea,
select {
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  padding: var(--spacing-sm);
  border: var(--border-style-normal);
  background-color: var(--color-white);
  color: var(--color-black);
  min-height: var(--touch-target-min);
  width: 100%;
}

input:focus,
textarea:focus,
select:focus {
  outline: var(--focus-outline);
  outline-offset: var(--focus-outline-offset);
}

label {
  display: block;
  font-family: var(--font-heading);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-sm);
  text-transform: uppercase;
  margin-bottom: var(--spacing-xs);
}

.form-group { margin-bottom: var(--spacing-lg); }

/* Toggle Switch */
.toggle-switch input[type="checkbox"] {
  appearance: none;
  width: 60px;
  height: 30px;
  border: var(--border-style-normal);
  background-color: var(--color-white);
  position: relative;
  cursor: pointer;
}

.toggle-switch input[type="checkbox"]::before {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  background-color: var(--color-black);
  border: var(--border-style-thin);
  top: 2px;
  left: 2px;
}

.toggle-switch input[type="checkbox"]:checked::before {
  left: 32px;
}

.toggle-switch input[type="checkbox"]:checked {
  background-color: var(--color-green);
}

/* ============================================
   FOCUS INDICATORS (ACCESSIBILITY)
   ============================================ */

*:focus-visible {
  outline: var(--focus-outline);
  outline-offset: var(--focus-outline-offset);
}

.btn:focus-visible,
.alert-card:focus-visible,
.market-card:focus-visible {
  outline: var(--border-thick) solid var(--color-yellow);
  outline-offset: 0;
}

/* ============================================
   RESPONSIVE - TABLET
   ============================================ */

@media (max-width: 1200px) {
  :root {
    --sidebar-width: 100%;
    --header-height: 70px;
  }

  .app-main {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .alert-sidebar {
    border-right: none;
    border-bottom: var(--border-style-normal);
    max-height: 300px;
    position: static;
    display: flex;
    overflow-x: auto;
    gap: var(--spacing-xs);
  }

  .alert-card {
    min-width: 280px;
    flex-shrink: 0;
  }

  .market-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .modal-panel {
    width: 90%;
    padding: var(--spacing-lg);
  }
}

/* ============================================
   RESPONSIVE - MOBILE
   ============================================ */

@media (max-width: 768px) {
  :root {
    --header-height: auto;
    --spacing-xl: 24px;
    --spacing-xxl: 32px;
  }

  .app-header {
    flex-direction: column;
    align-items: flex-start;
    padding: var(--spacing-md);
    gap: var(--spacing-md);
  }

  .header-filters {
    width: 100%;
  }

  .header-filters .btn-pill { flex: 1; }

  .app-metrics-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
    padding: var(--spacing-md);
  }

  .alert-sidebar {
    flex-direction: column;
    max-height: none;
  }

  .alert-card {
    min-width: auto;
    width: 100%;
  }

  .market-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm);
  }

  .hero-section { padding: var(--spacing-lg); }
  .hero-headline { font-size: var(--font-size-xl); }

  .modal-backdrop { padding: 0; }

  .modal-panel {
    width: 100%;
    height: 100vh;
    max-height: none;
    border: none;
    padding: var(--spacing-md);
  }

  .chart-canvas { height: 200px; }

  /* Stack table cells on mobile */
  table, thead, tbody, th, td, tr { display: block; }

  thead tr {
    position: absolute;
    top: -9999px;
    left: -9999px;
  }

  tr {
    margin-bottom: var(--spacing-md);
    border: var(--border-style-normal);
  }

  td {
    border: none;
    border-bottom: var(--border-style-hairline);
    position: relative;
    padding-left: 50%;
  }

  td::before {
    content: attr(data-label);
    position: absolute;
    left: var(--spacing-sm);
    font-weight: var(--font-weight-bold);
    text-transform: uppercase;
  }
}

/* ============================================
   UTILITY CLASSES
   ============================================ */

.hidden { display: none !important; }
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.flex { display: flex; }
.flex-column { flex-direction: column; }
.flex-wrap { flex-wrap: wrap; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }

.gap-xs { gap: var(--spacing-xs); }
.gap-sm { gap: var(--spacing-sm); }
.gap-md { gap: var(--spacing-md); }
.gap-lg { gap: var(--spacing-lg); }

.mt-md { margin-top: var(--spacing-md); }
.mt-lg { margin-top: var(--spacing-lg); }
.mb-md { margin-bottom: var(--spacing-md); }
.mb-lg { margin-bottom: var(--spacing-lg); }

.p-md { padding: var(--spacing-md); }
.p-lg { padding: var(--spacing-lg); }

.w-full { width: 100%; }
.h-full { height: 100%; }

/* Screen reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* ============================================
   PRINT STYLES
   ============================================ */

@media print {
  .app-header,
  .app-metrics-bar,
  .alert-sidebar,
  .btn,
  .modal-backdrop {
    display: none !important;
  }

  .app-main { grid-template-columns: 1fr; }
  .market-grid { grid-template-columns: repeat(2, 1fr); }
  .market-card { page-break-inside: avoid; }
}
```

---

# QUICK START TOMORROW

1. **Copy CSS** - Save the CSS above to `static/css/neo-brutalist.css`
2. **Inject into Streamlit** - Use `st.markdown()` with `unsafe_allow_html=True`
3. **Build page by page** - Start with Overview, then Alert Feed, etc.
4. **Use component classes** - Apply `.card`, `.btn`, `.alert-*` classes to elements
5. **Test responsiveness** - Check at 1200px and 768px breakpoints





