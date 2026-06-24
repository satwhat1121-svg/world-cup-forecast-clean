#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
STATE = BASE / 'state' / 'latest.json'
SITE = BASE / 'site'

HTML = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>2026 World Cup Forecast</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background:#08111f; color:#eef3ff; }
    .wrap { max-width: 1000px; margin: 0 auto; padding: 24px; }
    h1,h2 { margin-bottom: 8px; }
    .muted { color:#a9b7d0; }
    .card { background:#101b2d; border-radius:14px; padding:18px; margin:16px 0; }
    table { width:100%; border-collapse: collapse; font-size:14px; }
    th, td { padding:8px 10px; border-bottom:1px solid #24324a; text-align:left; }
    th { color:#8cc8ff; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px,1fr)); gap:16px; }
    code { background:#0b1423; padding:2px 6px; border-radius:6px; }
    a { color:#8cc8ff; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>2026 FIFA World Cup Forecast</h1>
    <p class="muted">Independent public-data model. Built from FIFA public feeds and World Football Elo. Not affiliated with FIFA or any proprietary forecast service.</p>
    <div id="app"></div>
  </div>
<script>
const data = __DATA__;
function pct(x){ return (x==null ? '—' : x.toFixed(1) + '%'); }
function table(rows, cols){
  return `<table><thead><tr>${cols.map(c=>`<th>${c.label}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${c.render?r[c.key]===undefined?c.render(undefined,r):c.render(r[c.key],r):(r[c.key]??'')}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
const titleCols = [
  {key:'team', label:'Team'},
  {key:'win_world_cup', label:'Win WC', render:v=>pct(v)},
  {key:'reach_final', label:'Final', render:v=>pct(v)},
  {key:'reach_semifinal', label:'Semi', render:v=>pct(v)},
  {key:'advance_from_group_or_r32', label:'Advance', render:v=>pct(v)}
];
const matchCols = [
  {key:'match', label:'Match'},
  {key:'home_win', label:'Home', render:v=>pct(v)},
  {key:'draw', label:'Draw', render:v=>pct(v)},
  {key:'away_win', label:'Away', render:v=>pct(v)},
  {key:'most_likely_score', label:'Likely score'}
];
const r32Cols = [
  {key:'match_number', label:'#'},
  {key:'home_slot', label:'Home slot'},
  {key:'home_team', label:'Home team', render:(v)=>v||'TBD'},
  {key:'away_slot', label:'Away slot'},
  {key:'away_team', label:'Away team', render:(v)=>v||'TBD'}
];
let groupsHtml = '';
for (const [group, rows] of Object.entries(data.group_tables)) {
  groupsHtml += `<div class="card"><h3>${group}</h3>${table(rows, [
    {key:'team', label:'Team'}, {key:'played', label:'P'}, {key:'wins', label:'W'}, {key:'draws', label:'D'},
    {key:'losses', label:'L'}, {key:'gf', label:'GF'}, {key:'ga', label:'GA'}, {key:'gd', label:'GD'}, {key:'points', label:'Pts'}
  ])}</div>`;
}
document.getElementById('app').innerHTML = `
  <div class="card">
    <div><strong>Generated:</strong> ${data.generated_at}</div>
    <div><strong>Simulations target:</strong> ${data.simulation_count.toLocaleString()}</div>
    <div><strong>Model notes:</strong> ${data.notes.join(' ')}</div>
  </div>
  <div class="card">
    <h2>Top title odds</h2>
    ${table(data.title_odds.slice(0,12), titleCols)}
  </div>
  <div class="card">
    <h2>Upcoming matches</h2>
    ${table(data.upcoming_matches, matchCols)}
  </div>
  <div class="card">
    <h2>Projected Round of 32</h2>
    <p class="muted">Slot resolution uses FIFA's official Annex C third-place lookup together with the public bracket placeholders and current group tables.</p>
    ${table(data.round_of_32 || [], r32Cols)}
  </div>
  <h2>Group tables</h2>
  <div class="grid">${groupsHtml}</div>
  <div class="card">
    <h2>Sources</h2>
    <ul>${data.sources.map(s=>`<li><a href="${s.url}">${s.name}</a></li>`).join('')}</ul>
  </div>
`;
</script>
</body>
</html>'''


def main():
    SITE.mkdir(exist_ok=True)
    data = json.loads(STATE.read_text())
    (SITE / 'index.html').write_text(HTML.replace('__DATA__', json.dumps(data)), encoding='utf-8')
    print(SITE / 'index.html')

if __name__ == '__main__':
    main()
