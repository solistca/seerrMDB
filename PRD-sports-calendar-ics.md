# PRD: Sports Schedule → Apple Calendar (.ics) Generator

> Note: this document is unrelated to the Seerr application itself. It's saved
> in this repo at the user's request purely to preserve session context for a
> personal side task, so a future Claude Code session can pick it up with no
> lost context. It is not part of Seerr's product documentation.

## Status: DONE for Wrexham AFC 2026-27 (`.ics` generated and delivered)

## Background

The user wants a repeatable process to generate a single `.ics` file that
imports into Apple Calendar with every match/game a sports team plays in a
season, so they don't have to enter events one at a time by hand. First
concrete case: **Wrexham AFC**, all competitions, this season.

## Requirements (confirmed with user)

1. **Scope**: all competitions the team is entered in this season (for
   Wrexham: league + FA Cup + EFL Trophy + any League/Carabao Cup, playoffs
   if applicable) — not just the league season.
2. **Data sourcing**: no source is provided by the user. It must be
   researched, and **every match's date and time must be cross-verified
   against two independent sources** (e.g. official club site vs. ESPN vs.
   BBC Sport vs. the competition's own site) before being included. Do not
   silently pick one source if two disagree — flag the conflict.
3. **Unscheduled times**: if a match's date is known but no kickoff/start
   time has been announced yet (common for later cup rounds not yet drawn),
   **include it anyway** as an all-day event with the time marked "TBD" —
   do not drop it from the file.
4. **Time zone conversion**: convert each match's local kickoff time to
   **Pacific Time**, correctly handling DST — the UK and US DST transition
   dates don't align (UK ends BST last Sunday of October; US ends PDT first
   Sunday of November), so do not hand-compute a fixed offset. Build the
   `.ics` with `DTSTART`/`DTEND` using `TZID=America/Los_Angeles` plus a
   proper embedded `VTIMEZONE` block (standard PST/PDT transition rules) so
   Apple Calendar renders the correct Pacific time regardless of device
   timezone settings.
5. **No reminders**: events should have no `VALARM` block — user explicitly
   does not want alerts.
6. **Reusability**: the user wants to reuse this exact process for other
   teams/sports in the future (mentioned: Chicago Bears, Manchester United,
   "any other sport team I deem appropriate"). The process is meant to be a
   repeatable two-step pattern, not a one-off script tied to Wrexham:
   - **Step 1 (research)**: an agent searches the web, compiles the full
     fixture list, cross-verifies every match against two sources, and
     writes a structured JSON file (schema below).
   - **Step 2 (build)**: a separate step reads that JSON and generates the
     `.ics` file (timezone conversion, TBD-match handling, no alarms). This
     step is sport-agnostic and doesn't change between teams.
7. Deliver the finished `.ics` file to the user as a downloadable file.

## Data schema (interface between Step 1 and Step 2)

```json
{
  "team": "<team name>",
  "sport": "<sport>",
  "season": "<season string>",
  "competitions": ["..."],
  "generated_at": "<ISO datetime>",
  "matches": [
    {
      "competition": "...",
      "date": "YYYY-MM-DD",
      "start_time_local": "HH:MM or 'TBD'",
      "timezone_note": "e.g. 'UK local (GMT/BST as applicable)'",
      "opponent": "...",
      "home_or_away": "home | away",
      "venue": "... or 'TBD'",
      "sources_checked": ["source name/url", "source name/url"],
      "verified": true,
      "note": "only present if there was a conflict between sources"
    }
  ],
  "undetermined": [
    "free-text notes on rounds/matches that exist but have no opponent/date yet"
  ]
}
```

## Reusable agent (created, but not yet usable in this environment)

A subagent definition was created at `~/.claude/agents/sports-schedule-researcher.md`
(user-level Claude Code config, **outside this git repo** — not tracked by
version control, since it's a Claude Code tool config file, not project code)
implementing the Step 1 research brief above in a team/sport-agnostic way.

**Known limitation discovered this session**: Claude Code loads custom
subagent definitions from `~/.claude/agents/` only at session start. Since
this is a fresh cloud/remote execution environment per session, a subagent
file created mid-session is not available until a *new session in the same
persistent environment* starts — and a brand-new session also does not carry
over this conversation's context (sessions never share history unless the
same session is resumed). Net effect: the saved agent file could not be
exercised this session. If working from a local Claude Code install where
`~/.claude` persists across normal restarts, this limitation may not apply
the same way — worth re-verifying in that context.

**Practical fallback used instead**: a one-off `general-purpose` Agent
invocation with the same brief embedded in the prompt, functionally
equivalent for a single run, just not registered as a named reusable agent
type in this environment.

## Work completed this session

- Plan for the two-step process approved by the user (see conversation
  history / this PRD for the equivalent content).
- `sports-schedule-researcher` agent definition written (see above; not
  exercised).
- `CLAUDE.md` added to this repo (separate, unrelated task) — committed as
  `5000cfc`.

## Work completed — Wrexham AFC run (this session)

1. Ran Step 1 research via a one-off `general-purpose` Agent using the brief
   above. Output saved as `wrexham-afc-2026-27-fixtures.json` (Step 1/Step 2
   interface data, matches the schema). 47 matches found across EFL
   Championship, FA Cup, and EFL Cup, each cross-verified against 2-3
   independent sources (club site, Wikipedia, BBC/Sky/ESPN/SI.com, EFL.com).
   Two undetermined items recorded (FA Cup 3rd Round opponent — draw not yet
   made; possible play-off matches, contingent on final league position).
   No TBD-time matches in this run — every dated match already had a
   confirmed kickoff.
2. Built `build_ics.py` — sport-agnostic Step 2 script implementing all
   requirements: converts each UK-local kickoff to `America/Los_Angeles` via
   `zoneinfo` (no hand-computed offset), embeds a standard `VTIMEZONE`
   PST/PDT block, emits TBD matches as all-day `VALUE=DATE` events, no
   `VALARM` blocks, RFC5545 line folding.
3. Validated the output by parsing it with the Python `icalendar` library:
   47 events, balanced BEGIN/END VEVENT, VTIMEZONE present, zero VALARM.
   Spot-checked the Oct 30 2026 fixture (UK already back to GMT, US still on
   PDT — the exact DST-mismatch case called out in requirement 4) and
   confirmed the Pacific offset is correct (7 hours, not a naive 8).
4. Delivered `wrexham-afc-2026-27.ics` to the user.

## Next steps for a future run (Chicago Bears, Man Utd, etc.)

Only Step 1 changes: give the `general-purpose` Agent a new brief (team,
sport, season, competitions) using the same brief template as this run, save
the resulting JSON, then re-run `python3 build_ics.py <json> <output.ics>` —
Step 2 is unchanged and sport-agnostic.
