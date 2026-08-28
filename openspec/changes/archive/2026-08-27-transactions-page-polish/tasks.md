# Tasks

## 1. Filter behavior (spec-driven)
- [x] 1.1 Narrow `TypeFilter` to `'trade' | 'waiver' | 'free_agent'` and remove the `All` entry
      from `TYPE_FILTERS` in `frontend/src/features/transactions/transactions.tsx`.
- [x] 1.2 Default the filter state to `'trade'` (`useState<TypeFilter>('trade')`).
- [x] 1.3 Simplify the wire filter to `t.type === typeFilter` (drop the `'all'` branch).

## 2. Direction A visual restyle
- [x] 2.1 Replace the raw filter buttons with a segmented control carrying a per-type icon.
- [x] 2.2 Add a per-type icon + accent-color map; use it for the transaction-type chip instead
      of the single `Repeat` icon.
- [x] 2.3 Restyle `TransactionCard` (Direction A): color-accented type chip, team panels with
      avatars, `↔` swap glyph between trade sides, FAAB/pick as tags. Keep the existing
      trade-vs-waiver/free-agent add/drop logic.
- [x] 2.4 Restyle `SummaryTable` header/rows, avatar emphasis, and Total column; preserve the
      sticky-header pattern and Season Standings avatar/color reuse.

## 3. Tests
- [x] 3.1 Add scenario(s) to `transactions.feature` + steps: default shows only Trades, no "All"
      option, and selecting Waivers / Free Agents narrows the list.
- [x] 3.2 Update existing scenarios' selectors as needed for the restyled markup (prefer
      role/text queries). Run `npx vitest run src/features/transactions/`.

## 4. Lint & validate
- [x] 4.1 `npm run format:fix` and `npm run lint` from `frontend/`.
- [x] 4.2 `openspec validate transactions-page-polish --strict`.
