# PRC Window Workbench + Risk Briefing UI Design

## Context

Current feedback says the sidebar selection controls feel rough, the page has too many competing elements, and the dashboard does not yet give engineers a strong reason to choose it over Spotfire.

The accepted direction is the V4 mockup: keep a familiar analysis workbench, but add a concise lag-aware risk briefing at the top and simplify controls into a readable query summary.

## Assumptions

- Target users are process/yield engineers who already understand Spotfire-style filtering and chart grids.
- The product should not look like a flashy prediction app. It should feel like a trustworthy engineering tool with a stronger default answer.
- The main differentiator is not chart creation itself. It is the ability to connect FAB trackout, delayed EDS target availability, predicted recent risk, suggested process window, and next checks in one workflow.
- Existing Vue 3 + Vite + ECharts structure should remain in place. This design should be achievable with scoped frontend changes before deeper backend/API expansion.

## Success Criteria

- A first-time reviewer can understand the current analysis condition without reading a dense sidebar.
- The first screen answers: what is risky, what feature appears to drive it, what window looks safer, and what check should be done next.
- Engineers can still see enough configuration detail to trust the result.
- Advanced controls such as matching, grade/category filters, grouped targets, and split mode remain available but do not dominate the default screen.
- The dashboard preserves Spotfire-like workbench familiarity while making the lag-aware risk briefing the distinctive hook.

## Chosen Approach

Use a **Workbench + Streamlined Controls** layout.

The left side becomes a compact query panel. It shows current scope, selected targets, ranked features, and an advanced filter entry point. It should not show every select box and every list in its expanded state by default.

The main content keeps a workbench grid: window chart, driver rank, time series, and condition comparison. Above that grid, add a risk briefing band with the strongest product hook:

- Lag-aware risk
- Top driver
- Suggested window
- Next check
- Trust check

## Alternatives Considered

### Guided Window Control Room

This made the product story clear and gave a stronger "wow" moment, but it reduced the familiar workbench feel. It risks looking too much like a prediction product instead of an engineering analysis tool.

### Process Risk Briefing

This pushed the wow point hardest: predicted gap, at-risk wafers, action queue, and potential recovery. It was rejected as too aggressive for the current product maturity and demo context.

### Spotfire-Like Workbench Only

This would feel familiar, but it would not sufficiently answer the boss's feedback about the missing hook. It risks becoming "Spotfire, but custom."

## Layout Design

### Left Query Panel

The default sidebar should show selected state, not every possible control.

Sections:

- Product identity: `Process Window`, current view label.
- Primary action: `Edit query`.
- Current query summary: line, product, FAB step, category, FAB date range, and EDS observed-through range.
- Targets: selected targets and grouped target badges.
- Features: selected and ranked candidate features, with the strongest driver visually emphasized.
- Advanced filters: collapsed entry for matching, metro grade/category, split mode, category feature values, and reset actions.

The full editing experience can be a drawer or modal opened by `Edit query`. This avoids burying the analysis behind a long form while preserving precise control when needed.

### Risk Briefing Band

Place this immediately under the page title.

Cards:

- `Lag-aware risk`: predicted recent target gap versus observed baseline, with model fit shown nearby.
- `Top driver`: highest-ranked feature and correlation/significance state.
- `Suggested window`: best-supported safer X range and bin sample count.
- `Next check`: recommended split or drill-down such as `EQP_CH split`.
- `Trust check`: observed support, extrapolation rate, and missing-Y gap.

The band should use calm engineering language. Avoid implying causal certainty. Prefer "appears related", "suggested", "predicted recent gap", and "check next".

### Workbench Grid

The main grid should keep familiar analytical surfaces:

- Window chart: Y average by X bin, DC/user/suggested window markers.
- Driver rank: ranked features by target relation.
- Time series: observed target, predicted recent target, and Y-missing zone.
- Condition compare: split values ranked by target mean and sample count.

Detailed combo rows, table, and interaction analysis can remain below this first-screen workbench area.

## Data Flow

The design should reuse current API outputs where possible:

- `/api/binned` for window chart bins and suggested safer ranges derived from existing bin statistics.
- `/api/timeseries` for observed target, feature series, missing-Y zone, and existing estimate metadata.
- `/api/table` for Cpk/Ppk and condition comparison support.
- `/api/drivers` for top driver and driver rank.
- `/api/raw` for CSV handoff from the current query.

If an exact "suggested window" is not yet an explicit backend field, frontend can initially derive it from binned rows using a conservative rule: prefer bins with sufficient `wafer_count`, lower target mean for bad-rate targets, and in-spec/within-DC support. This should be clearly labeled as suggested, not optimized.

## Trust And Error Handling

Risk briefing must show confidence context whenever it uses predicted Y:

- observed sample count
- model fit such as R² when available
- extrapolation rate when available
- EDS observed-through date or missing-Y gap

If prediction quality is weak, the briefing should degrade gracefully:

- Show "insufficient prediction confidence"
- Keep workbench charts visible
- Replace suggested window with "review observed window only"
- Keep export/share available

## Visual Style

Use a restrained engineering palette:

- neutral surfaces and borders
- dark emphasis only for the primary risk card
- limited red for risk, green for suggested/supported window, blue for system actions
- no decorative hero graphics or oversized marketing composition

Controls should be dense but not cramped. The sidebar should read as a query summary, not a form dump.

## Implementation Scope

In scope for the first implementation pass:

- Redesign sidebar into streamlined query summary plus collapsed advanced filters.
- Add top risk briefing band above existing insight panels.
- Reorder first-screen content so workbench charts appear before lower-priority panels.
- Keep existing APIs and data contracts unless a small derived field is necessary.
- Preserve existing chart components where practical.

Out of scope for this design pass:

- New backend ML models.
- Full workflow/task assignment.
- Real-time monitoring or alerts.
- Replacing all existing combo row behavior.
- Large app-wide component library rewrite.

## Verification Plan

- Run frontend build.
- Smoke test default query flow.
- Confirm empty/error/loading states still render.
- Check that sidebar text does not overflow in Korean labels.
- Check desktop and narrower viewport layouts.
- Verify risk briefing values match existing binned/timeseries/table/driver data, or are clearly marked unavailable.

## Open Decisions For Implementation Planning

- Whether `Edit query` opens a modal, drawer, or expands the sidebar in place.
- Exact rule for deriving `Suggested window` from binned data.
- Whether the first implementation should include Korean UI copy or use mixed Korean/English technical labels.
- Whether interaction analysis remains below the fold or becomes a tab in the workbench grid.
