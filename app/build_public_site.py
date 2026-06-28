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
    .wrap { max-width: 1440px; margin: 0 auto; padding: 24px; }
    h1,h2,h3 { margin-bottom: 8px; }
    .muted { color:#a9b7d0; }
    .card { background:#101b2d; border-radius:14px; padding:18px; margin:16px 0; }
    table { width:100%; border-collapse: collapse; font-size:14px; }
    th, td { padding:8px 10px; border-bottom:1px solid #24324a; text-align:left; }
    th { color:#8cc8ff; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px,1fr)); gap:16px; }
    code { background:#0b1423; padding:2px 6px; border-radius:6px; }
    a { color:#8cc8ff; }
    .bracket-wrap { overflow-x:auto; }
    .bracket-stage-labels { display:grid; grid-template-columns: 1.35fr 1fr .9fr .8fr .8fr .9fr 1fr 1.35fr; gap:18px; margin-bottom:14px; color:#8cc8ff; font-size:13px; font-weight:bold; min-width:1460px; }
    .bracket { display:grid; grid-template-columns: 1.35fr 1fr .9fr .8fr .8fr .9fr 1fr 1.35fr; gap:18px; align-items:start; min-width:1460px; }
    .round-col { display:flex; flex-direction:column; gap:10px; }
    .round-col.offset-1 { padding-top:42px; }
    .round-col.offset-2 { padding-top:102px; }
    .round-col.offset-3 { padding-top:166px; }
    .match-box { position:relative; background:#0c1526; border:1px solid #24324a; border-radius:12px; padding:10px; min-height:74px; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02); }
    .match-title { font-size:12px; color:#8cc8ff; margin-bottom:6px; text-transform:uppercase; letter-spacing:.02em; }
    .team-line { display:flex; justify-content:space-between; gap:8px; font-size:13px; padding:3px 0; }
    .team-line strong { color:#fff; font-weight:600; }
    .connector-col { display:flex; flex-direction:column; gap:10px; }
    .connector-col.offset-1 { padding-top:42px; }
    .connector-col.offset-2 { padding-top:102px; }
    .connector-col.offset-3 { padding-top:166px; }
    .connector-box { position:relative; min-height:74px; }
    .connector-box:before { content:''; position:absolute; top:50%; left:0; right:0; border-top:1px solid #2b3d5d; }
    .connector-box.left:after { content:''; position:absolute; right:0; top:50%; width:1px; height:42px; background:#2b3d5d; }
    .connector-box.right:after { content:''; position:absolute; left:0; top:50%; width:1px; height:42px; background:#2b3d5d; }
    .champion-stack { display:flex; flex-direction:column; gap:18px; padding-top:128px; }
    .champion-stack .match-box { background:linear-gradient(180deg, #13213c 0%, #0c1526 100%); border-color:#40639a; }
    .final-label { color:#8cc8ff; font-size:13px; font-weight:bold; text-align:center; margin-bottom:8px; }
    select { background:#0c1526; color:#eef3ff; border:1px solid #24324a; border-radius:8px; padding:8px 10px; }
    @media (max-width: 900px) {
      .wrap { padding: 16px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Soni World Cup Forecast</h1>
    <p class="muted">Live World Cup bracket and forecast built from public FIFA match data and World Football Elo. The Round of 32 is locked, and future rounds show the most likely teams and advancement probabilities from the current model.</p>
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
const r32ScenarioRows = (data.round_of_32_matchup_probs || []).map(r => `<option value="${r.team}">${r.team}</option>`).join('');
const pathScenarioRows = (data.knockout_path_probs || []).map(r => `<option value="${r.team}">${r.team}</option>`).join('');
function topN(slot, n=2){ return (data.bracket_slot_probs?.[String(slot)] || []).slice(0,n); }
function championTop(){ return (data.bracket_slot_probs?.champion || []).slice(0,3); }
function matchBox(title, lines){
  return `<div class="match-box"><div class="match-title">${title}</div>${lines.map(l=>`<div class="team-line"><strong>${l.team}</strong><span>${pct(l.probability)}</span></div>`).join('')}</div>`;
}
function r32MatchBox(matchNo){
  const p = data.round_of_32_win_probs?.[String(matchNo)];
  if(!p) return matchBox(`Match ${matchNo}`, [{team:r32ByMatch[matchNo]?.home_team || 'TBD', probability:null},{team:r32ByMatch[matchNo]?.away_team || 'TBD', probability:null}]);
  return matchBox(`Match ${matchNo}`, [
    {team:p.home_team, probability:p.home_advance},
    {team:p.away_team, probability:p.away_advance}
  ]);
}
const r32ByMatch = Object.fromEntries((data.round_of_32 || []).map(m => [m.match_number, m]));
const leftR32 = [74,77,73,75,83,84,81,82];
const rightR32 = [76,78,79,80,86,88,85,87];
const bracketHtml = `
  <div class="bracket-wrap">
    <div class="bracket-stage-labels">
      <div>Round of 32</div>
      <div>Round of 16</div>
      <div>Quarterfinals</div>
      <div>Semifinal</div>
      <div>Final / Champion</div>
      <div>Semifinal</div>
      <div>Quarterfinals</div>
      <div>Round of 16 / 32</div>
    </div>
    <div class="bracket">
      <div class="round-col">${leftR32.map(n => r32MatchBox(n)).join('')}</div>
      <div class="round-col offset-1">${[89,90,93,94].map(n => matchBox(`Match ${n}`, topN(n,3))).join('')}</div>
      <div class="round-col offset-2">${[97,98].map(n => matchBox(`Match ${n}`, topN(n,3))).join('')}</div>
      <div class="round-col offset-3">${matchBox('Match 101', topN(101,3))}</div>
      <div class="champion-stack"><div class="final-label">Final winner</div>${matchBox('Champion', championTop())}</div>
      <div class="round-col offset-3">${matchBox('Match 102', topN(102,3))}</div>
      <div class="round-col offset-2">${[99,100].map(n => matchBox(`Match ${n}`, topN(n,3))).join('')}</div>
      <div class="round-col offset-1">${[91,92,95,96].map(n => matchBox(`Match ${n}`, topN(n,3))).join('')}${rightR32.map(n => r32MatchBox(n)).join('')}</div>
    </div>
  </div>`;
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
    <h2>Probability bracket</h2>
    <p class="muted">The Round of 32 field is locked. Later rounds show the top projected teams in each future bracket slot based on the current simulation.</p>
    ${bracketHtml}
  </div>
  <div class="card">
    <h2>Projected Round of 32</h2>
    <p class="muted">Slot resolution uses FIFA's official Annex C third-place lookup together with the public bracket placeholders and current group tables.</p>
    ${table(data.round_of_32 || [], r32Cols)}
  </div>
  <div class="card">
    <h2>Round of 32 scenario generator</h2>
    <p class="muted">Choose a team to see its estimated Round of 32 opponent distribution from the current simulation.</p>
    <select id="scenarioTeam"><option value="">Select a team</option>${r32ScenarioRows}</select>
    <div id="scenarioOutput" style="margin-top:12px;"></div>
  </div>
  <div class="card">
    <h2>Knockout path probabilities</h2>
    <p class="muted">Choose a team to see the most likely opponents later in the bracket, conditional on reaching each stage.</p>
    <select id="pathTeam"><option value="">Select a team</option>${pathScenarioRows}</select>
    <div id="pathOutput" style="margin-top:12px;"></div>
  </div>
  <h2>Group tables</h2>
  <div class="grid">${groupsHtml}</div>
  <div class="card">
    <h2>Sources</h2>
    <ul>${data.sources.map(s=>`<li><a href="${s.url}">${s.name}</a></li>`).join('')}</ul>
  </div>
`;
const scenarioSelect = document.getElementById('scenarioTeam');
const scenarioOutput = document.getElementById('scenarioOutput');
const pathSelect = document.getElementById('pathTeam');
const pathOutput = document.getElementById('pathOutput');
function renderScenario(team){
  const row = (data.round_of_32_matchup_probs || []).find(r => r.team === team);
  if(!row){ scenarioOutput.innerHTML = '<div class="muted">No scenario data available.</div>'; return; }
  scenarioOutput.innerHTML = table(row.possible_opponents, [
    {key:'opponent_team', label:'Possible opponent'},
    {key:'probability', label:'Chance', render:v=>pct(v)}
  ]);
}
function renderPath(team){
  const row = (data.knockout_path_probs || []).find(r => r.team === team);
  if(!row){ pathOutput.innerHTML = '<div class="muted">No knockout path data available.</div>'; return; }
  const stageBlock = (title, rows) => `<div style="margin:14px 0;"><strong>${title}</strong>${rows && rows.length ? table(rows, [{key:'opponent_team', label:'Possible opponent'}, {key:'probability', label:'Chance', render:v=>pct(v)}]) : '<div class="muted" style="margin-top:8px;">No data available.</div>'}</div>`;
  pathOutput.innerHTML = stageBlock('Quarterfinal opponents', row.quarterfinal_opponents) + stageBlock('Semifinal opponents', row.semifinal_opponents) + stageBlock('Final opponents', row.final_opponents);
}
scenarioSelect?.addEventListener('change', e => renderScenario(e.target.value));
pathSelect?.addEventListener('change', e => renderPath(e.target.value));
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
