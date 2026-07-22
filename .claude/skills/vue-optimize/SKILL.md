---
name: vue-optimize
description: Audits Vue 3 component structure in client/src for performance anti-patterns and code-reuse opportunities, then reports prioritized, actionable findings. Use when asked to audit, review, or optimize Vue components/views for performance or duplication (not for one-off bug fixes - use vue-expert directly for those).
---

# Vue Component Structure & Optimization Audit

Read-only analysis skill. It produces a prioritized report; it does not edit `.vue` files
itself. If the user wants findings applied, delegate the actual edits to the **vue-expert**
subagent per this project's CLAUDE.md rule ("ANY time you need to create or significantly
modify a .vue file, you MUST delegate to vue-expert") - hand it findings one at a time with
file:line and the suggested fix, don't dump the whole report on it at once.

## Scope

- `client/src/views/*.vue`
- `client/src/components/*.vue`
- `client/src/composables/*.js`
- `client/src/App.vue` (global styles/shared patterns)
- `client/src/main.js` (routes - context for which views exist)
- `client/src/api.js` (context for data-fetching patterns)

## Process

1. **Inventory**: Glob for all `.vue` files and `composables/*.js` under `client/src`.
2. **Read each component** and record for it:
   - Size (LOC) and template nesting depth (`v-for`/`v-if` stacking)
   - Props/emits surface
   - Composables it imports and uses (or reimplements instead of using)
   - Whether it does its own data fetch with local `loading`/`error`/`data` refs
   - Local helper functions (formatting, filtering, sorting) defined inline vs imported
   - Computed vs method usage for template-bound derived values
3. **Cross-component comparison**: diff the recorded patterns across files to find near-identical
   blocks repeated 3+ times - these are the real reuse opportunities, not single occurrences.
4. If there are more than ~5 components to read, delegate the read/inventory step to the
   **Explore** subagent (research only, no edits) rather than reading every file inline -
   ask it to return the structural facts above per file, not opinions.
5. Write the findings as a single prioritized report (format below). Don't fix anything yet.

## Performance checklist

Flag concretely, with file:line, when found - not as generic advice:

- **Method calls in template** instead of `computed()` — recomputes on every render
  (`{{ calculateTotal() }}` vs `const total = computed(...)`)
- **`v-for` keyed by index** (or missing `:key` entirely) — breaks on reorder/insert/delete
- **Deep watchers** (`{ deep: true }`) on large objects/arrays where a narrower watch or a
  computed would do
- **Expensive work inside `v-for`** (filtering, formatting, date parsing per-row) that isn't
  memoized — should be precomputed once into a computed array of view-models
- **Large unfiltered lists rendered without pagination/virtualization** — flag any table
  rendering the full dataset (e.g. all 250 orders) with no windowing
- **Duplicate `.filter()`/`.reduce()` passes** over the same source array split across multiple
  `computed()` properties that could share one upstream computed
- **Inline object/array/function literals in template bindings** (`:style="{...}"`,
  `@click="() => fn(x)"`) — new reference every render, defeats memoization downstream
- **Non-debounced search/filter inputs** driving a computed/watch on every keystroke over a
  non-trivial dataset

## Code-reuse checklist

- **Duplicated fetch/loading/error boilerplate** (the `loading`/`error`/`data` ref triple +
  try/catch/finally shown in the vue-expert template) repeated across views instead of a shared
  `useAsyncData`/`useApiResource` composable
- **Duplicated formatting helpers** (currency, date, percentage) defined per-component instead
  of one shared `client/src/utils/format.js` — check this specifically, since inconsistent
  currency formatting (locale mixing) has already been observed across Inventory/Orders/Finance
  in this codebase
- **Duplicated filter-application logic** re-deriving warehouse/category/status matches instead
  of going through the existing `useFilters` composable — check whether every view that has
  filters actually uses it or silently reimplements the same conditionals
- **Repeated KPI/stat-tile markup** (label + big number + goal line, as seen on Overview/Finance/
  Restocking) that could become one `StatCard.vue`
- **Repeated data-table shell** (header row, empty state, loading row) duplicated per view
  instead of a shared table component/slot pattern
- **Repeated inline SVG chart boilerplate** that could be one small chart component or composable

## What NOT to flag

This is a demo app — prioritize clarity over premature optimization. Don't flag:
- A pattern that appears only once or twice (not real duplication yet)
- Micro-optimizations with no measurable effect at this data scale
- Anything that would require introducing a new dependency

## Output format

```markdown
# Vue Component Audit

**Components scanned**: [count] ([list of files])

## Performance

1. **[Title]** - [file.ext:line] - Severity: High/Medium/Low
   - Current: [what's there]
   - Why it matters: [concrete cost]
   - Suggested fix: [short code sketch]

## Code Reuse

1. **[Title]** - occurs in [file:line, file:line, file:line]
   - Pattern: [what's duplicated]
   - Suggested extraction: [composable/component name + shape]

## Top 3 Next Actions
1. ...
2. ...
3. ...
```

End with an offer to delegate the top findings to **vue-expert** for implementation, one at a
time, if the user wants them applied.
