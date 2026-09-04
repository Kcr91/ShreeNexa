# Frontend Terminal Shell Runtime Fix

## Problem

The browser rendered the React shell without the global terminal stylesheet and
without registering built-in widgets. The result was unstyled document-flow
HTML and `Widget not found` errors for valid shipped layout entries.

## Acceptance criteria

1. Importing the application root loads the global theme and reset stylesheet.
2. Importing the application root registers every shipped built-in widget.
3. The default dashboard renders its market clock, watchlist, and backtest
   summary without a missing-widget alert.
4. The production bundle contains a generated CSS asset.
5. The application fills the viewport with the dark terminal shell at desktop
   and laptop viewport sizes without horizontal document overflow.
6. Built-in metadata registers synchronously while each widget implementation
   remains lazy-loaded in a separate production chunk.
7. Frontend typecheck, tests, production build, and browser inspection pass.

## Boundaries

- Do not modify persisted user layouts.
- Do not change backend, broker, risk, credentials, or deployment behavior.
- Preserve unrelated changes in the primary `main` worktree.
