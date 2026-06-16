# design-sync notes — internship-matcher-dev

## Setup facts
- CRA app (not a library) — no `dist/`, no `.d.ts` output (tsconfig has `noEmit: true`)
- Synth-entry mode: `--entry ./src/ds-entry.ts` (barrel file committed at `src/ds-entry.ts`)
- `componentSrcMap` required — without it `[ZERO_MATCH]` fires (no package `.d.ts` to scan)
- Tailwind must be compiled before running build: `npx tailwindcss -i src/index.css -o src/.tailwind.compiled.css --config tailwind.config.js`
  - Output is gitignored; re-run on every sync
- Playwright was installed at `~/.cache/ms-playwright/chromium_headless_shell-1228` (Playwright 1.61.0)

## Component decisions
- `Header` excluded — needs `@clerk/react` (useUser, UserButton) + `react-router-dom`; can't render without full auth context
- `ResumeUploadForm` excluded — complex form with API calls + auth state
- `AnimatedHero`, `FadeUp`, `BuilderBlock`, `ClosingCTA`, `HonestStats`, `HowItActuallyWorks`, `ResultsPreview`, `TestJobDisplay`, `McpSetupDropdown`, `OnThisPage` excluded — landing page / page-specific
- `Card` and `JobCard` use `cardMode: column` — they're wider than a standard grid cell
- 4 floor-card components (CodeSnippet, JobCard→authored later, LoadingSpinner, ThemeProvider) — fine as-is

## Re-sync steps
```sh
cd frontend
npx tailwindcss -i src/index.css -o src/.tailwind.compiled.css --config tailwind.config.js
mkdir -p .ds-sync && cp -r "<skill-base-dir>"/package-build.mjs "<skill-base-dir>"/package-validate.mjs "<skill-base-dir>"/package-capture.mjs "<skill-base-dir>"/resync.mjs "<skill-base-dir>"/lib "<skill-base-dir>"/storybook .ds-sync/
echo '{"name":"ds-sync-deps","private":true}' > .ds-sync/package.json
cd .ds-sync && npm i esbuild ts-morph @types/react && cd ..
node .ds-sync/resync.mjs --config .design-sync/config.json --node-modules ./node_modules --entry ./src/ds-entry.ts --out ./ds-bundle --remote .design-sync/.cache/remote-sync.json
```

## Re-sync risks
- `src/ds-entry.ts` is the sync surface — new components need to be added here AND to `componentSrcMap` in config
- Tailwind config changes (new custom tokens) require re-compiling the CSS before running build
- `ThemeProvider` is both a component in the bundle AND the preview wrapper (`cfg.provider`) — if it's renamed or moved, update both `componentSrcMap` and `provider.component`
- `JobCard` preview uses hardcoded sample `Job` data — if the `Job` interface changes, update `.design-sync/previews/JobCard.tsx`
- `CodeSnippet` and `Logo` have floor cards (no authored preview); they work fine but won't show in the component picker with rich previews
- Font families (Source Sans 3, Source Serif 4, JetBrains Mono) load from Google Fonts at runtime — they render correctly in designs but won't show in offline/air-gapped environments
