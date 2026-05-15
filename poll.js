import { readFile, writeFile } from "node:fs/promises";

const CONFIG_FILE  = process.env.CONFIG_FILE  || "config.json";
const HISTORY_FILE = process.env.HISTORY_FILE || "snapshots.json";
const RETAIN_DAYS  = 14;
const TIMEOUT_MS   = 25_000;
const UA = "twp-leaderboard-tracker/1.0";

async function fetchJson(url) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA }, signal: ctrl.signal });
    if (!r.ok) throw new Error(`${url} -> HTTP ${r.status}`);
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

async function main() {
  const cfg = JSON.parse(await readFile(CONFIG_FILE, "utf8"));
  const lb  = cfg.leaderboard ?? "frumaSrPlayers";
  const lim = cfg.resultLimit ?? 20;

  const raw = await fetchJson(`https://api.wynncraft.com/v3/leaderboards/${lb}?resultLimit=${lim}`);

  // Normalize: array of { rank, name, uuid, sr, completions, gambits, supportRank, restricted }
  const players = [];
  for (const [rankStr, e] of Object.entries(raw)) {
    const rank = Number(rankStr);
    if (!Number.isFinite(rank)) continue;
    const meta = e.metadata || {};
    players.push({
      rank,
      name:        e.restricted ? null : (e.name ?? null),
      uuid:        e.uuid ?? null,
      sr:          Number(e.score ?? 0),
      completions: Number(meta.completions ?? 0),
      gambits:     Number(meta.gambits ?? 0),
      supportRank: e.supportRank ?? null,
      restricted:  !!e.restricted,
    });
  }
  players.sort((a, b) => a.rank - b.rank);

  const ts = new Date().toISOString();
  const snapshot = { ts, players };

  let history = { snapshots: [] };
  try { history = JSON.parse(await readFile(HISTORY_FILE, "utf8")); } catch {}
  if (!Array.isArray(history.snapshots)) history.snapshots = [];
  history.snapshots.push(snapshot);

  const cutoff = Date.now() - RETAIN_DAYS * 86400_000;
  history.snapshots = history.snapshots.filter(s => new Date(s.ts).getTime() >= cutoff);
  history.updated = ts;
  history.config = cfg;

  await writeFile(HISTORY_FILE, JSON.stringify(history, null, 2) + "\n");
  const top = players[0];
  console.log(`OK ${lb} -> ${HISTORY_FILE} top=${top?.name ?? "?"} sr=${top?.sr ?? 0} (n=${players.length}, snaps=${history.snapshots.length})`);
}

main().catch((e) => { console.error(e); process.exit(1); });
