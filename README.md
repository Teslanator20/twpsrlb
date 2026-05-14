# twpsrlb — Fruma SR Race

Top 20 of the Wynncraft `frumaSrPlayers` leaderboard, refreshed every 5 minutes.

- `config.json` — leaderboard + tracking parameters (highlight names)
- `poll.js` — fetches the leaderboard, appends `snapshots.json`
- `index.html` — Top 8 spotlight + full leaderboard + per-player trends
- `.github/workflows/poll.yml` — cron, triggered externally via cron-job.org → workflow_dispatch
