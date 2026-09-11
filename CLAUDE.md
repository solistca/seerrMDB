# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Seerr is a media request management app (a Jellyfin/Plex/Emby-integrated fork lineage from Overseerr/Jellyseerr) that talks to Sonarr/Radarr and other services. It's a single Next.js + Express app: Next.js serves the React frontend (`src/`) and a custom Express server (`server/`) handles the API, background jobs, and DB access, all in one process (see `server/index.ts`).

## Commands

- `pnpm dev` — run the dev server (nodemon + ts-node on `server/index.ts`, watches `server/` and `seerr-api.yml`; Next.js handles frontend HMR internally).
- `pnpm build` — full production build (`build:next` then `build:server`); `build:server` compiles `server/` with `tsc`, copies templates/locale files, then rewrites path aliases with `tsc-alias`.
- `pnpm start` — run the production build (`dist/index.js`).
- `pnpm lint` / `pnpm lintfix` — ESLint over `server/` and `src/`.
- `pnpm format` / `pnpm format:check` — Prettier over the whole repo.
- `pnpm typecheck` — runs both `typecheck:server` (server `tsconfig.json`) and `typecheck:client` (root `tsconfig.json`); these are separate TypeScript projects with separate configs, so a type error may only show up under one.
- `pnpm test` — runs `server/test/index.mts`, a thin wrapper around Node's built-in `node:test` runner. By default it globs all `server/**/*.test.ts`; pass file paths to run a subset, e.g. `pnpm test server/routes/auth.test.ts`, and `-m <pattern>` to filter by test name. There is no frontend/component test suite.
- `pnpm cypress:open` — open Cypress for E2E tests (`cypress/`). `pnpm cypress:build` builds the app and prepares a test DB (`cypress:prepare`) first.
- `pnpm i18n:extract` — extract/update translation source strings from `formatjs` message definitions in `src/` and `server/` into the locale JSON files. CI's i18n check (`bin/check-i18n.js`) fails a PR if this hasn't been run after changing translated strings.
- `pnpm migration:generate` / `migration:create` / `migration:run` — TypeORM migration commands. **Every schema change needs two migrations**, one under `server/migration/sqlite/` and one under `server/migration/postgres/` — see the "Migrations" section of `CONTRIBUTING.md` for the exact procedure (it requires spinning up a real Postgres instance to generate the Postgres migration).

## Architecture

### Server (`server/`)

- `index.ts` — process entry point: initializes the Next.js app, runs the Overseerr→Seerr migration check, initializes the TypeORM `DataSource`, runs migrations (production only), loads settings, starts i18n, sets up the DNS cache/proxy agent, then mounts Express routes and starts scheduled jobs.
- `datasource.ts` — TypeORM `DataSource` config. Picks SQLite or Postgres based on `DB_TYPE`/`NODE_ENV`; SQLite is the default. Test runs (`NODE_ENV=test`) use an in-memory SQLite DB with schema sync instead of migrations.
- `entity/` — TypeORM entities (`User`, `MediaRequest`, `Media`, `Season`, `Issue`, `Blocklist`, `Watchlist`, settings entities, etc.) — the DB schema.
- `routes/` — Express routers, one per resource (`movie.ts`, `tv.ts`, `request.ts`, `user/`, `settings/`, etc.), assembled in `routes/index.ts`. Route handlers validate against `seerr-api.yml` (OpenAPI spec, validated at runtime via `express-openapi-validator`) — **update `seerr-api.yml` when adding/changing an endpoint**, or requests will be rejected by the validator.
- `api/` — outbound API clients for third-party services: TheMovieDB, TVDB, Plex/PlexTV, Jellyfin, Tautulli, Sonarr/Radarr (`servarr/`), ratings providers, GitHub.
- `lib/scanners/` — library-sync logic per media server (Plex, Jellyfin) and per Arr app (Sonarr, Radarr); `lib/availabilitySync.ts` and `lib/watchlistsync.ts` reconcile local DB state against these external sources.
- `lib/notifications/` — notification dispatch; `agents/` has one file per notification channel (Discord, Email, Slack, Telegram, webhook, web push, etc.), all registered onto a shared `notificationManager` in `index.ts`.
- `lib/settings/` — app settings persistence/schema, including `JobId`-keyed cron schedules for scheduled jobs and `migrations/` for settings-file migrations (distinct from DB migrations).
- `lib/permissions.ts` — bitmask `Permission` enum; permission checks (`and`/`or` combinators) gate route/UI access throughout the app.
- `job/schedule.ts` — registers all `node-schedule` cron jobs (library scans, refresh tokens, availability/watchlist sync, etc.) driven by the cron strings in settings; conditional on which media server type is configured.
- `middleware/auth.ts` — `isAuthenticated`/`checkUser` middleware used across routes for session- and permission-based access control.
- Path alias `@server/*` maps to `server/*` (see `server/tsconfig.json`); server code always imports other server code via `@server/...`, never relative paths across directories (enforced by `no-relative-import-paths` ESLint rule, `allowSameFolder` only).

### Frontend (`src/`)

- Next.js Pages Router (`src/pages/`) — file-based routes mirror the app's URL structure (`movie/`, `tv/`, `requests/`, `settings/`, `users/`, etc.).
- `src/components/` — one directory per feature/component (not flat files), colocating a component with its subcomponents.
- `src/context/` — global React context: `UserContext` (current user/permissions), `SettingsContext` (public app settings), `LanguageContext`, `InteractionContext`.
- `src/hooks/` — shared hooks, notably `useSettings`/`useUser` (wrap the contexts) and data-fetching hooks built on `swr`.
- Path alias `@app/*` maps to `src/*` (see root `tsconfig.json`); same relative-import restriction as the server side applies.
- i18n: UI strings are defined via `react-intl`/`formatjs` `defineMessages` inline in components; `pnpm i18n:extract` (or `server/i18n/extractMessages.ts` for server-side strings) harvests them into `src/i18n/locale/` and `server/i18n/locale/` JSON. Translations themselves are managed externally via Weblate — don't hand-edit non-English locale files.

### Cross-cutting

- The OpenAPI spec `seerr-api.yml` at the repo root is the single source of truth for the HTTP API surface — both request validation (server) and generated API docs (`/api-docs`) come from it.
- SQLite and Postgres are both first-class supported databases; anything touching schema or raw SQL needs to work on both engines.
- Both `server/` and `src/` share one root `.prettierrc.js`/ESLint config but have **separate TypeScript projects** (`server/tsconfig.json` vs. root `tsconfig.json`) — don't assume a type-only change compiles everywhere just because one `tsc` run passed.

## Maintaining this file

When a change alters a command, the architecture, or a convention documented above, update the relevant section here as part of that same change — don't let this file drift out of sync with the codebase.

## Contribution norms (from `CONTRIBUTING.md`)

- PRs target `develop`, never `master`, and PR titles must follow Conventional Commits.
- AI-assisted contributions must be disclosed in the PR description, and PR/review text must be written by the human contributor in their own words, not pasted model output.
