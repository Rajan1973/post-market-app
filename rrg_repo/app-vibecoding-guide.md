# India RRG — App Vibecoding Guide

> Living project handbook for the India Relative Rotation Graph application.
>
> Update this document whenever the application, database schema, calculation engine, data pipeline, or product scope changes. It is written so that a future maintainer can understand the project even years after the current implementation.

## Document control

| Field | Value |
|---|---|
| Project | India RRG — Weekly Relative Rotation |
| Primary artifact | outputs/rrg_app_updated.html |
| Companion manual | outputs/rrg-user-manual.html |
| Current document version | 1.5 |
| Last reviewed | 2 September 2026 |
| Application type | Standalone browser-based analytical dashboard |
| Market | Indian equities and NSE indices |
| Timeframe | Weekly |
| Primary data project | Dedicated RRG-Data Supabase project |
| Source project | Nifty500data, read-only |
| Intended use | Market-structure research and education |
| Investment advice | No |

## 1. Project purpose

India RRG is an interactive browser application for studying the relative rotation of:

- Selected Nifty indices and sectoral indices against a benchmark.
- Constituent stocks within a selected Nifty index.
- Weekly RRG snapshots based on Friday week-ending data.
- Historical movement through configurable tails and an eight-week snapshot slider.
- Relative strength and momentum through the four RRG quadrants.

The application is descriptive. It is not a trading system, buy/sell signal generator, portfolio-management system, or investment advice.

The core question is:

> Is an index or stock outperforming its benchmark, and is that relative performance improving or weakening?

## 2. High-level architecture

The project has two data domains.

### Nifty500data

This is the existing source data warehouse. It is a read-only dependency for this application. RRG work must never modify, delete, or overwrite its data.

### RRG-Data

This is the dedicated Supabase project for:

- RRG instruments.
- Benchmarks and index universes.
- Constituent relationships.
- RRG-specific weekly prices.
- Calculated RRG metrics.
- Future calculation-run and data-quality metadata.

Conceptual flow:

    Nifty500data.daily_prices
            |
            | read-only extraction
            v
    RRG-Data weekly aggregation
            |
            v
    Friday-close selection and validation
            |
            v
    RRG V2 calculation engine
            |
            v
    rrg_metrics_v2
            |
            v
    India RRG browser application

The frontend should display values returned by rrg_metrics_v2. It should not independently recalculate RRG metrics.

## 3. Supabase project

### 3.1 Current identity

| Property | Value |
|---|---|
| Project purpose | RRG-Data |
| Supabase project reference | lwspbnufodlvvnrokaux |
| REST base URL | https://lwspbnufodlvvnrokaux.supabase.co/rest/v1/ |
| Frontend access | Public/publishable key with read-only policies |
| Source project | Nifty500data |
| Source write policy | No writes |

The application currently contains a publishable Supabase key. This is safe only if database policies prevent unauthorized writes and sensitive data exposure. A service-role key, database password, or private credential must never be placed in the HTML.

### 3.2 Expected security model

The public application should be able to read:

- Active instruments.
- Active benchmarks.
- RRG metrics.
- Constituent relationships required for drill-down.
- Weekly data only when the frontend needs it.

The public application should not be able to:

- Insert, update, or delete market data.
- Modify benchmark membership.
- Modify calculation runs.
- Modify RRG metrics.
- Modify source-project data.
- Access administrative credentials.

Long-term security improvements:

- Keep all writes in server-side jobs or Supabase Edge Functions.
- Use explicit read-only Row Level Security policies.
- Separate public presentation views from ingestion tables.
- Add automated policy tests.
- Never expose a service-role key in browser code.

## 4. Database objects

The exact live schema must be rechecked whenever this guide is revised. The following is the intended RRG-Data model and the current application contract.

### 4.1 rrg_instruments

Instrument master for indices and stocks visible to the app.

| Field | Purpose |
|---|---|
| id | Internal RRG instrument identifier |
| source_instrument_id | Link to the source instrument where available |
| symbol | Display and market symbol |
| name | Human-readable name |
| instrument_type | Stock or index classification |
| is_active | Controls app availability |

The frontend uses this table to map metric rows to readable names.

### 4.2 rrg_benchmarks

Defines benchmark choices and index universes.

| Field | Purpose |
|---|---|
| id | Benchmark or universe identifier |
| symbol | Market or internal symbol |
| name | Display name |
| benchmark_type | Benchmark or index classification |
| is_active | Controls availability |

Current product behavior exposes only two benchmark choices:

- Nifty 50, selected by default.
- Nifty 500.

Other active Nifty indices are used as sidebar drill-down universes rather than benchmark-selector choices.

### 4.3 rrg_constituents

Maps a selected Nifty index to constituent instruments.

| Field | Purpose |
|---|---|
| benchmark_id | Parent Nifty index |
| instrument_id | Constituent stock |
| Membership dates | Optional historical membership support |
| Weight fields | May be unavailable or null in the current data |

Example:

    Nifty Auto
        - M&M
        - TVS Motor
        - Maruti
        - other constituents

The drill-down RRG compares these stocks against their selected parent index, not automatically against Nifty 50.

### 4.4 rrg_weekly_prices

RRG-specific weekly price series.

The intended source process is:

1. Read daily prices from Nifty500data.
2. Group observations by instrument and calendar week.
3. Use the last observed trading session as week_end.
4. Preserve Friday dates when Friday is a trading session.
5. Handle market holidays using the actual final trading session.
6. Write the derived series only into RRG-Data.

Weekly OHLCV rules:

| Weekly field | Rule |
|---|---|
| Open | First valid daily open |
| High | Maximum daily high |
| Low | Minimum daily low |
| Close | Last valid daily close |
| Adjusted close | Last valid daily adjusted close |
| Volume | Sum of daily volume |
| week_end | Last observed trading date in the week |

RRG calculations should use adjusted weekly close where available to reduce false relative-strength jumps caused by corporate actions.

### 4.5 rrg_metrics_v2

Primary calculated output consumed by the current application.

| Field | Meaning |
|---|---|
| instrument_id | Plotted instrument |
| benchmark_id | Benchmark or parent universe |
| week_end | Weekly observation date |
| rs_ratio | Normalized relative-strength ratio |
| rs_momentum | Normalized momentum of relative strength |
| quadrant | Leading, Improving, Weakening, or Lagging |
| direction | Direction indicator where available |
| universe_type | INDEX or STOCK |
| calculation_version | Calculation-engine identifier |

Current calculation version:

    v2-ema10-jdk-public

The frontend should filter by this version explicitly so old calculations are not mixed with current values.

### 4.6 Legacy objects

The project history included an earlier rrg_metrics object and a V1 method named:

    ema10-roc10-norm26

V1 should be treated as legacy unless a deliberate comparison feature is built. The current application is intended to use rrg_metrics_v2 and v2-ema10-jdk-public.

### 4.7 Week availability

The project history refers to a Friday-only availability object such as rrg_week_picker. Whether the frontend reads that object directly or derives available dates from rrg_metrics_v2, the product rule is:

- Only Friday week-ending dates appear in the eight-week slider.
- Holiday handling must be documented by the data pipeline.
- Arbitrary dates must not be silently mixed with Friday-close snapshots.

## 5. RRG calculation model

### 5.1 Concept

RRG uses two normalized axes:

- RS-Ratio: the relative-strength trend of the instrument versus its benchmark.
- RS-Momentum: the momentum of that relative-strength trend.

Both axes are centered around 100.

The implementation is a transparent public approximation inspired by common RRG methodology. It is not a claim to reproduce the proprietary JdK implementation.

### 5.2 Relative strength

For instrument A and benchmark B:

    RS = 100 x AdjustedClose(A) / AdjustedClose(B)

The weekly instrument and benchmark series must be date-aligned.

### 5.3 RS-Ratio

The V2 formulation uses EMA smoothing and normalization around a 100 baseline.

Conceptually:

    RS smooth = EMA10(RS)
    RS-Ratio  = 100 x RS smooth / EMA10(RS smooth)

The database calculation is authoritative. If the engine changes, update this section and the calculation version together.

### 5.4 RS-Momentum

Momentum measures whether the RS-Ratio trend is rising or fading.

Conceptually:

    RS-Momentum = 100 x RS-Ratio / EMA10(RS-Ratio)

The stored rrg_metrics_v2 values are authoritative for the frontend.

### 5.5 Quadrants

| Condition | Quadrant | Meaning |
|---|---|---|
| RS-Ratio >= 100 and RS-Momentum >= 100 | Leading | Strong relative performance and improving momentum |
| RS-Ratio >= 100 and RS-Momentum < 100 | Weakening | Still relatively strong, but momentum is fading |
| RS-Ratio < 100 and RS-Momentum < 100 | Lagging | Relatively weak and still losing momentum |
| RS-Ratio < 100 and RS-Momentum >= 100 | Improving | Relatively weak, but momentum is turning upward |

Typical clockwise rotation:

    Improving -> Leading -> Weakening -> Lagging -> Improving

### 5.6 Warm-up history

EMA and normalization require historical warm-up. The calculation must not run only on the eight weeks visible in the UI.

The pipeline should retain enough historical observations before producing current metrics. The normalization window and any EMA warm-up rules must be recorded in the calculation-run metadata.

### 5.7 Data-quality requirements

Before calculating RRG:

- Align instrument and benchmark weekly dates.
- Check for stale index series.
- Check missing or partial trading weeks.
- Identify holidays separately from missing data.
- Prefer adjusted close.
- Record calculation version.
- Record source and run metadata.
- Reconcile new weekly bars against the source warehouse where possible.
- Do not silently fill missing observations with stale prices.

## 6. Frontend architecture

### 6.1 Current implementation

The current app is a standalone HTML artifact:

    outputs/rrg_app_updated.html

It contains:

- HTML structure.
- Embedded CSS.
- Embedded JavaScript.
- Supabase REST calls.
- SVG chart rendering.
- TradingView chart drawer integration.

There is currently no required build step.

### 6.2 Main frontend state

The app tracks:

- Active benchmark: Nifty 50 or Nifty 500.
- Active sidebar universe: all Nifty indices or one selected Nifty index.
- Loaded metric rows.
- Historical rows grouped by instrument.
- Eight weekly snapshots.
- Selected names displayed on the chart.
- Enabled quadrants.
- Tail length.
- Selected chart point.
- Zoom scale.
- Open or closed TradingView drawer.

### 6.3 Data loading

The app reads:

1. Active instruments.
2. Active benchmarks.
3. V2 metrics for the current view.
4. The latest eight Friday snapshots.

The query contract is:

    table: rrg_metrics_v2
    calculation_version: v2-ema10-jdk-public
    universe_type: INDEX or STOCK
    benchmark_id: selected benchmark or parent index

Pagination is handled in the REST helper so the browser does not rely on a single 1,000-row response.

### 6.4 SVG chart

The graph is rendered as SVG to keep the application dependency-light.

The chart includes:

- Four colored background quadrants.
- Vertical and horizontal center axes at 100.
- Major grid lines.
- Numeric major interval labels.
- X-axis title: RS-Ratio (Relative Strength).
- Y-axis title: RS-Momentum.
- Instrument labels and colored points.
- Historical tail polylines.
- Clickable points for detail selection.
- Button-only zoom controls.

### 6.5 Zoom model

Zoom is controlled only through in-chart buttons:

- Zoom in.
- Zoom out.
- Reset zoom.

The visible axis range changes around the 100 center. Mouse-wheel zoom is intentionally not implemented.

### 6.6 Responsive layout

The layout consists of:

- Left sidebar for benchmark, tail, search, index drill-down, and quadrant filters.
- Main content for title, universe chip strip, eight-week slider, chart, rotation board, details, and FAQ.
- Right-side overlay drawer for the TradingView chart.

The sidebar collapses above the main content on smaller screens.

## 7. Features built

### 7.1 Benchmark selection

The benchmark selector contains:

- Nifty 50, default.
- Nifty 500.

It does not act as the index drill-down selector.

### 7.2 Index-level RRG

The default view plots the configured Nifty index universe against the selected benchmark.

The chip strip lists every index currently available in the index-level RRG. Each chip can be selected or deselected.

### 7.3 Sidebar drill-down

The sidebar contains:

- All Nifty indices.
- Individual Nifty indices.

Selecting an index changes the view to that index’s constituents.

Example:

    Sidebar: Nifty Auto
    Chart universe: Nifty Auto constituent stocks
    Benchmark: Nifty Auto

### 7.4 Selectable universe strip

The strip above the history slider:

- Lists all plotted indices or stocks.
- Shows quadrant color.
- Selects or deselects individual names.
- Provides Show all and Hide all controls.
- Updates the graph and four-column board.

### 7.5 Eight-week history slider

The slider:

- Uses the latest eight available Friday snapshots.
- Moves the complete RRG snapshot through time.
- Updates points, tails, date label, coverage, and board.
- Works in both index and constituent-stock views.

### 7.6 Historical tails

Each plotted instrument can display a tail showing recent movement. Tail length is adjustable from 2 to 12 weeks.

Tails provide visual context and do not change stored calculations.

### 7.7 Four-column rotation board

The board has four meaningful presentation columns:

| Board column | Quadrant | Interpretation |
|---|---|---|
| Money Flowing In | Improving | Weak, but gaining momentum |
| Building Strength | Leading | Strong and still rising |
| Losing Momentum | Weakening | Strong, but rolling over |
| Underperforming | Lagging | Weak and falling further |

Rows show:

- Instrument name.
- Relative score derived from RS-Ratio displacement.
- Momentum score derived from RS-Momentum displacement.
- Relative-return indicator when available.
- Momentum-based fallback when a stored return field is unavailable.

Each row is clickable and keyboard accessible.

### 7.8 Instrument detail card

Selecting a chart point updates:

- Instrument name.
- RS-Ratio.
- RS-Momentum.
- Quadrant.

### 7.9 TradingView Lite drawer

Clicking an index or stock row opens a right-side sliding panel.

The panel includes:

- Selected instrument name.
- TradingView Lite weekly chart.
- NSE symbol mapping for common Nifty indices.
- Close button at the top-left.
- Escape-key close behavior.
- Note distinguishing TradingView display data from RRG V2 calculations.

This chart is a visual reference, not the source of RRG calculations.

### 7.10 Axis labels and zoom controls

The chart includes:

- X-axis label: RS-Ratio (Relative Strength).
- Y-axis label: RS-Momentum.
- Numeric major intervals on both axes.
- Zoom in, Zoom out, and Reset controls.
- No mouse-wheel zoom.

### 7.11 User watchlists

The sidebar contains three local watchlists:

- Watchlist-1
- Watchlist-2
- Watchlist-3

Each watchlist supports:

- A user-defined name.
- Comma-separated NSE stock-code entry.
- Validation against the active instrument master.
- Separate reporting of found and not-found codes.
- Editing and replacement of constituents.
- Local browser persistence.
- CSV export for external editing.
- CSV import for restoring or updating watchlists.
- A watchlist-only RRG view from the sidebar.

The optional “Include watchlist during Index Analysis” setting requests matching watchlist metrics alongside the index-level universe when those metrics exist in rrg_metrics_v2. It does not invent metrics that are absent from the database.

Watchlist data is stored in browser local storage, not in Supabase. Clearing browser site data can remove it; users should export the CSV as a backup.

### 7.12 TradingView studies and BSE mapping

The TradingView drawer requests a weekly Advanced Chart configuration with:

- RSI.
- MACD.
- Volume.

TradingView symbol selection prefers a BSE code. The current frontend includes a local mapping for common instruments and can use future bse_code or bse_symbol fields if those are added to the instrument master. The current documented instrument schema is NSE-oriented and does not guarantee a verified BSE code for every stock. Unmapped symbols need to be reconciled before relying on the external chart.

### 7.13 FAQ

The page includes an FAQ covering:

- What an RRG is.
- All four quadrant meanings.
- RS-Ratio and RS-Momentum.
- Covered sectors and benchmarks.
- Why the graph is not a buy/sell signal.

The research and education disclaimer must remain intact.

### 7.14 User manual

The companion manual is published as:

    outputs/rrg-user-manual.html

The app header contains a `User manual ↗` link that opens this file in a new tab. The manual is intentionally separate from the application so it can be read, printed, or updated without changing the RRG rendering code. It covers the purpose of RRG charts, quick start, every current control, index and stock workflows, watchlists, TradingView behavior, the V2 method, limitations, and responsible-use guidance.

The app and manual must remain in the same output directory so the relative links continue to work when the files are downloaded together or served from a static host.

### 7.15 Sharing and hosting

The application is a standalone HTML client, so it can be served through GitHub Pages or another static host. It requires browser network access to the RRG-Data Supabase REST endpoint and TradingView’s external chart embed. A local `file://` preview may behave differently from a hosted HTTPS page because of browser security policies.

ChatGPT Sites may also be a possible distribution route when the feature is available for the account or workspace. The current HTML should be treated as the reference implementation; importing or recreating it in a hosted site must be validated for Supabase requests, TradingView embeds, browser local storage, CSV import/export, and public-data exposure before publishing.

## 8. User workflows

### Index-level workflow

1. Open the app.
2. Keep Nifty 50 selected or choose Nifty 500.
3. Leave the sidebar on All Nifty indices.
4. Use the chip strip to choose indices.
5. Move the eight-week slider.
6. Adjust tail length.
7. Click a chart point for RRG details.
8. Click a board row for the TradingView drawer.
9. Use chart zoom buttons when needed.

### Constituent workflow

1. Select a Nifty index in the sidebar, such as Nifty Auto.
2. The app loads that index’s constituent stocks.
3. Use the stock chip strip to select or deselect constituents.
4. Move the eight-week slider.
5. Inspect chart points, tails, and the four-column board.
6. Click a stock row to open its TradingView chart.

## 9. Known limitations

### Data limitations

- The browser depends on RRG-Data availability and correctness.
- A stale or incomplete source series can produce misleading positions.
- Historical index membership and constituent weights may not be complete.
- Current membership is not automatically equivalent to historical membership.
- Holiday weeks require explicit calendar handling.
- Source Nifty500data remains read-only; all repair and aggregation must happen in RRG-Data.

### Calculation limitations

- V2 is a transparent public approximation, not proprietary JdK code.
- Results may differ from other providers because of:
  - Weekly sampling rules.
  - Adjusted-price sources.
  - Benchmark series.
  - EMA initialization.
  - Normalization windows.
  - Index membership dates.
  - Holiday and stale-data handling.
- The frontend trusts rrg_metrics_v2 and does not independently audit the mathematics.

### Frontend limitations

- A single HTML file becomes harder to maintain as features grow.
- The app requires network access to Supabase and TradingView.
- TradingView widget availability and symbol coverage are external dependencies.
- New index symbols may require additional mapping.
- The SVG chart is lightweight but less feature-rich than a specialist chart library.
- The board uses momentum displacement as a fallback when a stored relative-return field is unavailable.
- There are no user accounts, saved layouts, annotations, alerts, or portfolio integrations.
- There is no automated frontend test suite yet.
- Browser file-URL security policies may affect some local preview tools.

### Product limitations

- The graph is descriptive, not predictive.
- Rankings are not recommendations.
- No execution, position sizing, risk management, or backtesting is included.
- The app does not guarantee real-time data.
- The displayed date is a completed weekly snapshot, not an intraday reading.

## 10. Future scope

### Near-term priorities

1. Recheck the live Supabase schema against this guide.
2. Add formal data-quality status to each weekly snapshot.
3. Display source freshness and calculation-run time.
4. Complete TradingView symbol mapping for every supported index.
5. Add automated tests for Friday filtering, universe queries, quadrants, zoom, drawer behavior, and chip selection.
6. Add a TradingView loading and failure state.
7. Add a frontend-safe database view exposing only required metric columns.

### Medium-term priorities

- Move from one HTML file to a component-based application.
- Add URL state for benchmark, selected index, week, and visible names.
- Add accessible chart tooltips.
- Export a snapshot to CSV or image.
- Add historical membership and weights.
- Detect rotation events such as axis crossings and quadrant changes.
- Compare two Friday snapshots side by side.
- Add a data-quality dashboard.
- Add server-side caching and efficient metric views.

### Long-term possibilities

- Scheduled weekly ingestion and calculation runs.
- Supabase Edge Functions or a dedicated calculation service.
- Authentication and saved workspaces.
- Alerts for quadrant transitions.
- Portfolio holdings overlay.
- Backtesting of quadrant-transition rules, separated from descriptive analytics.
- Cross-provider reconciliation.
- Mobile-optimized layout.
- Versioned V1/V2/V3 calculation comparison.
- Observability, audit logs, and reproducible calculation manifests.

## 11. Maintenance rules

When changing the project:

1. Preserve the read-only boundary around Nifty500data.
2. Never replace V2 data with client-side approximations without documenting why.
3. Increment calculation_version whenever the formula changes.
4. Update database-contract sections when fields or tables change.
5. Keep Friday-only behavior explicit.
6. Keep benchmark and universe semantics explicit:
   - Nifty 50 and Nifty 500 are benchmark choices.
   - Individual Nifty indices are drill-down universes.
   - Constituent stocks are compared with their selected parent index.
7. Add a migration note for destructive or irreversible changes.
8. Run a syntax check after every HTML change.
9. Test index-level and stock-level flows separately.
10. Check a narrow viewport after layout changes.
11. Verify chart values come directly from the current metric version.
12. Preserve the FAQ disclaimer unless explicitly changed by the product owner.
13. Update the change log.

## 12. Change log

### Version 1.5 — 2 September 2026

- Added the standalone `rrg-user-manual.html` companion guide.
- Added a top-right `User manual ↗` link from the app to the manual.
- Documented the manual’s scope, same-folder relative-link requirement, and static-hosting behavior.
- Documented ChatGPT Sites as a possible future distribution route subject to account availability and compatibility testing.
- Updated document control to identify the companion manual and current review date.

### Version 1.4 — 1 September 2026

- Applied a modern quiet-finance-terminal visual treatment to the dashboard without changing the four RRG quadrant background colors.
- Added lavender styling to distinguish user-created watchlist selectors from Nifty index drill-down selectors.
- Preserved the compact two-row instrument selector behavior.
- Added stable distinct colors for instruments in the selector strip, plotted points, and historical tails.
- Constrained the TradingView Advanced Chart iframe and internal widget container to the drawer height to prevent detached blank panes.
- Kept weekly RSI, MACD, and Volume studies in the default TradingView configuration for every symbol change.

### Version 1.2 — 1 September 2026

- Changed the instrument selector strip to a compact two-row, wrapping layout with reduced chip typography.
- Added a watchlist Supabase fallback query by instrument ID when benchmark-specific watchlist metrics are unavailable.
- Ensured watchlist views refresh the graph and quadrant board from available RRG V2 stock metrics.
- Re-applied the default TradingView studies on every symbol change using the documented Advanced Chart configuration: RSI, MACD, and Volume.

### Version 1.1 — 1 September 2026

- Added three local user watchlists with editable names and NSE-code entry.
- Added database validation feedback for found and not-found stock codes.
- Added local browser persistence and CSV import/export for watchlists.
- Added optional inclusion of watchlist instruments during index analysis when matching V2 metrics are available.
- Added watchlist-only sidebar views.
- Updated TradingView drawer behavior to prefer BSE identifiers and request weekly RSI, MACD, and Volume studies.
- Documented the current limitation that the instrument schema does not yet expose a confirmed BSE-code column for every stock.

### Version 1.0 — 1 September 2026

- Created the first durable project handbook.
- Documented RRG-Data and Nifty500data separation.
- Documented the V2 metric contract.
- Documented Friday-close behavior.
- Documented index and constituent drill-down.
- Documented Nifty 50 and Nifty 500 benchmark restriction.
- Documented the selectable universe strip.
- Documented the eight-week slider and tails.
- Documented the four-column board.
- Documented chart axis labels and major intervals.
- Documented button-only zoom.
- Documented the TradingView Lite sliding drawer.
- Documented the FAQ and research-only disclaimer.
- Recorded current limitations and future scope.

## 13. Update template

### Version X.Y — YYYY-MM-DD

**Change**

- What changed?

**Why**

- Product, data, calculation, or maintenance reason.

**Files/tables affected**

- List affected artifacts.

**Compatibility**

- Does this affect old data, saved links, or existing users?

**Validation**

- What was checked?

**Known follow-up**

- Remaining limitation or next step.

## 14. Quick reference

| Question | Answer |
|---|---|
| What does the app show? | Weekly relative rotation of Nifty indices or constituent stocks |
| What are the benchmarks? | Nifty 50 and Nifty 500 |
| What is the default? | Nifty 50, All Nifty indices |
| How is drill-down selected? | Choose an index from the sidebar |
| What is the constituent benchmark? | The selected parent Nifty index |
| How many historical snapshots are exposed? | Eight latest Friday snapshots |
| Can names be hidden? | Yes, through the chip strip or Hide all |
| Can the graph be zoomed? | Yes, with Zoom in, Zoom out, and Reset |
| Does mouse-wheel zoom work? | No |
| What does the board show? | Money Flowing In, Building Strength, Losing Momentum, Underperforming |
| Where do RRG values come from? | rrg_metrics_v2 |
| What is the calculation version? | v2-ema10-jdk-public |
| Is Nifty500data modified? | No; it is read-only |
| Is the app investment advice? | No |
