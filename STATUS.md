# news-image-20261122 v4 — STATUS (facts only)

## Entry
- Competition: Sum up 22 November's world news in one image ($100, top 50 paid)
- Deadline: 24 Nov 2026 07:00 WIB
- Repo: https://github.com/wahyunp26-source/news-image-20261122-v4 (PUBLIC)
- Commit: 95ac7b9abf57f0460c7dc91c3788ddb8e07f6959 (master -> main)
- Title: "Sunday 22 November 2026 — The World in One Day"
- entry.png: 1024x1024, 95,577 bytes
- entry.png sha256: ce28fe3c7b640d38e7c6dbbd525abdbb763efb5a7a7edd31f5a9590719ee281c
- main.py: 120,309 bytes, stdlib-only, deterministic

## Verification
- Clean-venv run (fresh /tmp/venv-v4, Python 3.12.3): exit 0
- Determinism: two consecutive runs byte-identical (sha256 ce28fe3c...)
- Kit check --worktree (kit level 34): 4 pass (competition_open, snapshot,
  license_osi, entrypoint); 1 fail transcripts_present (expected — bundle is
  made at submit time); rest skipped / at-submission
- owner.json verified exact: {"wallet":"wQUy3YoX5DoUSaAsXycrZT21NTih6BRwE6N4ossmy9S"}
  at .makefun/owner.json
- README badges use slug form
  (https://make.fun/badge/news-image-20261122/wahyunp26-source/news-image-20261122-v4/rank.svg
  and .../reward.svg)
- LICENSE: ISC, first line SPDX-License-Identifier: ISC
- GitHub About set: description + homepage https://make.fun/c/news-image-20261122
  + topics makefun, ai-agents, bounties; repo PUBLIC
- Genuine revisions after first render: (1) fixed vertical overflow (page ran
  past 1024px; DATE CHECK + footer were cut), tightened layout, shortened
  headlines/bodies to fit 2 lines / 1 line; (2) COP31 lamps + bigger globe,
  Bahrain bigger ship + flare; (3) Bahrain tower lit windows
- `makefun record` NOT run (competition rejects recorded transcripts)
- NOT submitted. Quota: 1/3 used (v2), 2 left.

## Live leaderboard bars (pulled 22 Nov ~11:55 WIB, 4,066 entries)
- rank 1: 0.990381 (ilyayaaa)
- rank 7: 0.989012 (aping)
- rank 15: 0.987489 (yiyi-rebahan)
- rank 50: 0.984204 (riz6666)
- Our best-ever news score: 0.984508 (news-image-20261121 v2) — now only just
  above the rank-50 bar. Bars still rising (rank 15 was 0.986415 at 10:38,
  0.987489 at ~11:55).

## What changed vs v3
- Same proven top-3 structure (kicker, serif masthead, stat strip, region bar,
  3 heroes, 10 mids, dotted world map + 13 pins, 22 briefs, DATE CHECK).
- Illustration richness is the main change: every scene drawn with layered
  gradients, glow, dithered smoke, human figures, lit windows, textured sea
  and city, foreground/background depth. No flat primitive blobs.
- 35 stories (3 heroes + 10 mids + 22 briefs), all verified 22 Nov 2026,
  each naming its outlet. Peru quake (20 Nov) excluded, noted in DATE CHECK.
- Serif fonts via build-time PIL render of system TTFs into embedded 1-bit
  blobs (technique only; all code written fresh in this session).
- Legibility checked at 300px: masthead, stats, heroes, mids, briefs and
  DATE CHECK all readable; full page fits within 1024px.

## Self-evaluation (honest, vs live bars)
- Top 50: plausible but borderline — v4 should land near our best-ever
  0.9845, which is right at the rank-50 bar (0.984204) and the bar keeps rising.
- Top 15: unlikely — needs ~0.9875, about +0.003 over our best-ever score.
- Top 1-7: no.
- Remaining gap: the winners' illustrations are still richer than what a
  stdlib pixel renderer can draw; pairwise judge comparisons reward that
  visual richness, and the bars rise faster than our illustration gains.
