'use strict';

const $ = (id) => document.getElementById(id);
const state = { request: null, result: null, mode: 'salvage', revision: 0, resultRevision: -1, busy: false, defects: new Map() };
const dimensionFields = {width: 'width', depth: 'depth', min_width: 'min-width', min_depth: 'min-depth', height: 'height', thickness: 'thickness'};
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (value) => Number(value).toLocaleString('en', {maximumFractionDigits: 1});
const area = (value) => (value / 1e6).toFixed(3);

function showError(message) {
  $('error').hidden = !message;
  $('error').textContent = message || '';
}

function disableExports(disabled) {
  for (const id of ['download', 'download-csv', 'verify']) $(id).disabled = disabled;
}

function stale() {
  state.revision++;
  $('state-pill').textContent = 'Inputs changed · recalculate';
  $('state-pill').className = 'state-pill stale';
  $('fixture-label').textContent = 'EDITED INVENTORY · VERIFY YOUR MEASUREMENTS';
  $('verify-status').textContent = '';
  disableExports(true);
  showError('');
}

function syncInventoryJSON() { $('inventory-json').value = JSON.stringify(state.request.boards, null, 2); }

function renderInventory() {
  const container = $('inventory');
  container.replaceChildren();
  state.request.boards.forEach((board, index) => {
    const card = document.createElement('article');
    card.className = 'board-card';
    card.innerHTML = `<div class="board-title"><span class="board-swatch"></span><strong>${escapeHTML(board.label || board.id)}</strong><button type="button" class="remove-board" aria-label="Remove ${escapeHTML(board.label || board.id)}">×</button></div><div class="board-fields"><input type="number" min="1" max="10000" value="${Number(board.width)}" aria-label="${escapeHTML(board.label || board.id)} width"><span>×</span><input type="number" min="1" max="10000" value="${Number(board.height)}" aria-label="${escapeHTML(board.label || board.id)} height"></div><div class="board-meta"><span>${number(board.thickness)} mm · ${escapeHTML(board.grain === 'x' ? 'grain →' : 'rotatable')}</span><button type="button" class="defect-toggle">${board.defects.length ? `${board.defects.length} defect · clear` : state.defects.has(board.id) ? 'Restore defect' : 'No defects'}</button></div>`;
    const inputs = card.querySelectorAll('input');
    inputs[0].addEventListener('input', () => { board.width = Number(inputs[0].value); syncInventoryJSON(); stale(); });
    inputs[1].addEventListener('input', () => { board.height = Number(inputs[1].value); syncInventoryJSON(); stale(); });
    card.querySelector('.remove-board').addEventListener('click', () => { state.request.boards.splice(index, 1); renderInventory(); stale(); });
    card.querySelector('.defect-toggle').addEventListener('click', () => {
      if (board.defects.length) { state.defects.set(board.id, structuredClone(board.defects)); board.defects = []; }
      else if (state.defects.has(board.id)) board.defects = structuredClone(state.defects.get(board.id));
      else { document.querySelector('.advanced').open = true; $('inventory-json').focus(); return; }
      renderInventory(); stale();
    });
    container.append(card);
  });
  $('add-board').disabled = state.request.boards.length >= 6;
  syncInventoryJSON();
}

function readRequest() {
  const request = structuredClone(state.request);
  for (const [key, id] of Object.entries(dimensionFields)) request.design[key] = Number($(id).value);
  request.design.step = 10;
  request.kerf = Number($('kerf').value);
  return request;
}

function partLabel(id) {
  const item = state.result.parts.find((p) => p.id === id);
  return item ? item.label : String(id).replaceAll('-', ' ');
}

function sheetSVG(board, placements, index) {
  const w = board.width, h = board.height;
  const font = Math.max(13, Math.min(w, h) * 0.065);
  const colors = ['#bfd0a5', '#cad9b1', '#d6d7ae', '#a7bf96', '#b5c9a0'];
  const partShapes = placements.map((p, i) => {
    const cx = p.x + p.width / 2, cy = p.y + p.height / 2;
    const title = `${partLabel(p.part_id)}: ${number(p.width)} × ${number(p.height)} mm at ${number(p.x)}, ${number(p.y)}`;
    return `<g><title>${escapeHTML(title)}</title><rect x="${p.x}" y="${p.y}" width="${p.width}" height="${p.height}" fill="${colors[i % colors.length]}" stroke="#779360" stroke-width="1.5"/><text x="${cx}" y="${cy - font*.08}" text-anchor="middle" font-size="${font}" fill="#49603c" font-family="Georgia,serif">${escapeHTML(partLabel(p.part_id))}</text><text x="${cx}" y="${cy + font*1.22}" text-anchor="middle" font-size="${font*.6}" fill="#6f805a" font-family="Arial,sans-serif">${number(p.width)} × ${number(p.height)}${p.rotated ? ' ↻' : ''}</text></g>`;
  }).join('');
  const defects = (board.defects || []).map((d) => `<rect x="${d.x}" y="${d.y}" width="${d.width}" height="${d.height}" fill="url(#hatch-${index})" stroke="#b6806b" stroke-width="1"><title>Excluded defect: ${number(d.width)} × ${number(d.height)} mm</title></rect>`).join('');
  return `<svg viewBox="-3 -3 ${w+6} ${h+6}" role="img" aria-label="${escapeHTML(board.label || board.id)} cutting layout with ${placements.length} parts"><defs><pattern id="hatch-${index}" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#ead1b7"/><path d="M-2 2L2 -2M0 10L10 0M8 12L12 8" stroke="#b9826c" stroke-width="2"/></pattern><pattern id="wood-${index}" width="90" height="19" patternUnits="userSpaceOnUse"><path d="M0 9Q22 5 45 9T90 9" stroke="#c7b89c" fill="none" stroke-width=".5" opacity=".5"/></pattern></defs><rect width="${w}" height="${h}" fill="#e9dfc8" stroke="#bcb398" stroke-width="2"/><rect width="${w}" height="${h}" fill="url(#wood-${index})"/>${partShapes}${defects}</svg>`;
}

function renderDrawing() {
  if (!state.result) return;
  const result = state.result;
  const baseline = state.mode === 'baseline';
  const plan = baseline ? result.baseline : result;
  const boards = plan.boards;
  const feasible = plan.status === 'feasible';
  const selectedShape = baseline ? result.target : result.selected_design;
  const widthDelta = selectedShape ? selectedShape.width_mm - result.target.width_mm : 0;
  const depthDelta = selectedShape ? selectedShape.depth_mm - result.target.depth_mm : 0;
  if (state.resultRevision === state.revision) {
    $('state-pill').textContent = feasible ? baseline ? '✓ Fixed-brief geometry checked' : '✓ Geometry checked' : baseline ? 'Fixed brief unresolved' : 'No salvage fit found';
    $('state-pill').className = feasible ? 'state-pill' : 'state-pill failed';
  }
  if (baseline) {
    $('result-heading').textContent = feasible ? plan.new_boards ? 'The fixed brief uses new stock.' : 'The fixed brief already fits.' : 'No fixed-brief layout found.';
    $('result-description').textContent = `${number(result.target.width_mm)} × ${number(result.target.depth_mm)} mm, unchanged. ${feasible ? 'All five parts fit in this heuristic comparison.' : 'No checked comparison is available.'}`;
  } else {
    $('result-heading').textContent = feasible ? widthDelta === 0 && depthDelta === 0 ? 'Your brief. Already in the offcuts.' : `A ${number(Math.abs(widthDelta || depthDelta))} mm change. A second life.` : 'The brief needs more room.';
    $('result-description').textContent = feasible ? `${number(result.target.width_mm)} × ${number(result.target.depth_mm)} → ${number(selectedShape.width_mm)} × ${number(selectedShape.depth_mm)} mm. Same five-panel concept, ${widthDelta === 0 && depthDelta === 0 ? 'same dimensions' : 'an adjusted footprint'}.` : 'All five parts must fit. None of the sampled designs passed with this inventory.';
  }
  $('metric-new').textContent = feasible ? baseline ? String(plan.new_boards) : '0' : '—';
  $('metric-parts').textContent = feasible ? `${plan.placements.length} / ${result.parts.length}` : `0 / ${result.parts.length}`;
  $('metric-change').textContent = feasible ? `${widthDelta < 0 ? '−' : widthDelta > 0 ? '+' : ''}${number(Math.abs(widthDelta))} mm` : '—';
  $('proof-title').textContent = feasible ? baseline ? 'Fixed-brief geometry checked.' : 'Every part accounted for.' : 'No valid geometry certificate for this plan.';
  $('proof-text').textContent = 'The full proof export includes both plans and their separate checks.';
  renderAssembly(selectedShape || result.target);
  $('drawing-area').className = 'drawing-area' + (baseline ? ' baseline' : '');
  $('tab-salvage').classList.toggle('selected', !baseline);
  $('tab-baseline').classList.toggle('selected', baseline);
  $('tab-salvage').setAttribute('aria-selected', String(!baseline));
  $('tab-baseline').setAttribute('aria-selected', String(baseline));
  if (plan.status === 'no_fit' || !boards.length) {
    $('drawing-area').innerHTML = `<div class="no-fit"><strong>No checked layout found.</strong>${baseline ? 'The fixed brief could not be packed with the allowed new stock.' : 'Try a smaller minimum dimension, a larger offcut, or a different inventory.'}<br>This search result is not a proof of impossibility.</div>`;
  } else {
    $('drawing-area').innerHTML = boards.map((board, index) => {
      const placements = plan.placements.filter((p) => p.board_id === board.id);
      return `<div class="sheet"><div class="sheet-top"><b>${escapeHTML(board.label || board.id)}</b><span class="${board.new ? 'new-badge' : ''}">${board.new ? 'NEW STOCK' : 'RECLAIMED'}</span></div>${sheetSVG(board, placements, index)}<div class="sheet-bottom"><span>${number(board.width)} × ${number(board.height)} mm</span><span>${board.grain === 'x' ? 'GRAIN →' : 'ROTATION ALLOWED'}</span></div></div>`;
    }).join('');
  }
  const newCount = result.baseline.new_boards;
  const selected = result.selected_design;
  let insight;
  if (baseline) insight = newCount == null ? 'The baseline is unresolved. No purchased-material saving can be claimed.' : `Keeping the original ${number(result.target.width_mm)} × ${number(result.target.depth_mm)} mm brief uses ${newCount} new panel${newCount === 1 ? '' : 's'} in this heuristic plan, alongside any usable salvage. This is not a proven minimum.`;
  else if (selected) insight = `The ${number(selected.width_mm)} × ${number(selected.depth_mm)} mm second shape uses only your existing panels. ${result.search.feasible} of ${result.search.candidates} sampled designs passed the geometry check. The remaining material includes defects and kerf; it is not all reusable offcut.`;
  else insight = `No salvage-only fit was found among ${result.search.candidates} sampled designs. The planner keeps this failure visible instead of dropping a part or shrinking beyond your brief.`;
  $('insight').querySelector('p').textContent = insight;
}

function renderResult(result) {
  state.result = result;
  state.resultRevision = state.revision;
  const feasible = result.status === 'feasible';
  const selected = result.selected_design;
  const widthChange = feasible ? selected.width_mm - result.target.width_mm : null;
  const depthChange = feasible ? selected.depth_mm - result.target.depth_mm : null;
  $('state-pill').textContent = feasible ? '✓ Geometry checked' : 'No salvage fit found';
  $('state-pill').className = feasible ? 'state-pill' : 'state-pill failed';
  $('result-heading').textContent = feasible ? widthChange === 0 && depthChange === 0 ? 'Your brief. Already in the offcuts.' : `A ${number(Math.abs(widthChange || depthChange))} mm change. A second life.` : 'The brief needs more room.';
  $('result-description').textContent = feasible ? `${number(result.target.width_mm)} × ${number(result.target.depth_mm)} → ${number(selected.width_mm)} × ${number(selected.depth_mm)} mm. Same five-panel concept, ${widthChange === 0 && depthChange === 0 ? 'same dimensions' : 'an adjusted footprint'}.` : 'All five parts must fit. None of the sampled designs passed with this inventory.';
  $('metric-new').textContent = feasible ? '0' : '—';
  $('metric-parts').textContent = feasible ? `${result.placements.length} / ${result.parts.length}` : `0 / ${result.parts.length}`;
  $('metric-change').textContent = feasible ? `${widthChange > 0 ? '+' : widthChange < 0 ? '−' : ''}${number(Math.abs(widthChange))} mm` : '—';
  $('proof-title').textContent = feasible ? 'Every part accounted for.' : 'No valid salvage certificate.';
  $('proof-text').textContent = feasible ? 'Bounds, overlap, kerf, defects, grain & completeness checked.' : 'The export includes the failed search and the fixed-brief comparison.';
  const targetPartsArea = 2*result.target.width_mm*result.target.depth_mm + 3*(result.target.height_mm-2*result.target.thickness_mm)*result.target.depth_mm;
  const materialChange = feasible ? (100 * (targetPartsArea - result.metrics.material_area_mm2) / targetPartsArea).toFixed(1) : null;
  $('evidence-summary').textContent = feasible && result.baseline.new_boards != null ? `On this inventory, the original brief uses ${result.baseline.new_boards} new ${number(result.request.new_stock.width)} × ${number(result.request.new_stock.height)} mm panel${result.baseline.new_boards === 1 ? '' : 's'} (${area(result.baseline.purchased_area_mm2)} m² purchased) in the same heuristic. The second shape purchases none and contains ${materialChange}% less part area. These are different dimensions; the baseline is not a proven minimum.` : 'No reliable purchased-material reduction is available for this result. The fixed-brief plan and all search details are included in the export.';
  disableExports(false);
  $('verify').disabled = !feasible;
  renderDrawing();
}

function renderAssembly(d) {
  const w = d.width_mm, depth = d.depth_mm, h = d.height_mm, t = d.thickness_mm;
  const project = (x,y,z) => [x + y*.48, h-z-y*.35];
  const points = (list) => list.map((p) => project(...p).join(',')).join(' ');
  function cuboid(x,y,z,dx,dy,dz) {
    return `<polygon points="${points([[x,y,z],[x+dx,y,z],[x+dx,y,z+dz],[x,y,z+dz]])}" fill="#b6caa3" stroke="#6b855c" stroke-width="2"/><polygon points="${points([[x+dx,y,z],[x+dx,y+dy,z],[x+dx,y+dy,z+dz],[x+dx,y,z+dz]])}" fill="#93ae80" stroke="#6b855c" stroke-width="2"/><polygon points="${points([[x,y,z+dz],[x+dx,y,z+dz],[x+dx,y+dy,z+dz],[x,y+dy,z+dz]])}" fill="#d7e0bd" stroke="#6b855c" stroke-width="2"/>`;
  }
  const shapes = cuboid(0,0,0,w,depth,t) + cuboid(w-t,0,t,t,depth,h-2*t) + cuboid((w-t)/2,0,t,t,depth,h-2*t) + cuboid(0,0,t,t,depth,h-2*t) + cuboid(0,0,h-t,w,depth,t);
  $('assembly-preview').innerHTML = `<svg viewBox="-8 ${-depth*.35-8} ${w+depth*.48+16} ${h+depth*.35+30}" role="img" aria-label="${number(w)} by ${number(depth)} by ${number(h)} millimetre five-panel organizer concept"><title>Proportional concept, not an assembly or structural assessment</title>${shapes}<text x="${w/2}" y="${h+23}" text-anchor="middle" font-family="Arial,sans-serif" font-size="20" fill="#819372">${number(w)} mm</text></svg>`;
}

async function runPlan(event) {
  if (event) event.preventDefault();
  if (!state.request || state.busy) return;
  if (!$('plan-form').reportValidity()) return;
  const revision = state.revision;
  state.busy = true;
  $('solve-button').disabled = true;
  $('solve-button').firstElementChild.textContent = 'Searching the possibilities…';
  $('state-pill').textContent = 'Python is checking the geometry…';
  $('state-pill').className = 'state-pill';
  disableExports(true);
  showError('');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch('/api/solve', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(readRequest()),signal:controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The planner could not process this input.');
    if (revision !== state.revision) {
      $('state-pill').textContent = 'Inputs changed · recalculate';
      $('state-pill').className = 'state-pill stale';
      return;
    }
    state.mode = 'salvage';
    renderResult(data);
  } catch (error) {
    showError(error.name === 'AbortError' ? 'The planner timed out. Try fewer offcuts or a smaller design range.' : error.message);
    $('state-pill').textContent = 'Input needs attention';
    $('state-pill').className = 'state-pill failed';
    if (!state.result) $('drawing-area').innerHTML = '<div class="no-fit"><strong>The planner is unavailable.</strong>Check your connection and try again.</div>';
  } finally {
    clearTimeout(timeout);
    state.busy = false;
    $('solve-button').disabled = false;
    $('solve-button').firstElementChild.textContent = 'Find a second shape';
  }
}

async function loadExample() {
  if (state.busy) return;
  state.busy = true;
  state.revision++;
  $('state-pill').textContent = 'Loading the example…';
  $('state-pill').className = 'state-pill';
  $('solve-button').disabled = true;
  disableExports(true);
  try {
    const response = await fetch('/api/example');
    if (!response.ok) throw new Error('The example could not be loaded.');
    state.request = await response.json();
    state.defects.clear();
    state.revision++;
    for (const [key,id] of Object.entries(dimensionFields)) $(id).value = state.request.design[key];
    $('kerf').value = state.request.kerf;
    renderInventory();
    $('fixture-label').textContent = 'ILLUSTRATIVE INVENTORY · NOT FIELD MEASURED';
    $('verify-status').textContent = '';
    state.busy = false;
    await runPlan();
  } catch (error) { state.busy = false; $('solve-button').disabled = false; showError(error.message); $('state-pill').textContent = 'Unable to load example'; }
}

function download(content, filename, mime) {
  const url = URL.createObjectURL(new Blob([content], {type:mime}));
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$('plan-form').addEventListener('submit', runPlan);
for (const id of [...Object.values(dimensionFields),'kerf']) $(id).addEventListener('input', stale);
$('reset').addEventListener('click', () => { if (!state.busy) loadExample(); });
$('tab-salvage').addEventListener('click', () => { state.mode = 'salvage'; renderDrawing(); });
$('tab-baseline').addEventListener('click', () => { state.mode = 'baseline'; renderDrawing(); });
for (const id of ['tab-salvage','tab-baseline']) $(id).addEventListener('keydown', (event) => { if (['ArrowLeft','ArrowRight'].includes(event.key)) { event.preventDefault(); const next = id === 'tab-salvage' ? $('tab-baseline') : $('tab-salvage'); next.click(); next.focus(); } });
$('add-board').addEventListener('click', () => {
  if (state.request.boards.length >= 6) return;
  state.request.boards.push({id:`offcut-${Date.now()}`,label:`Offcut ${state.request.boards.length+1}`,width:600,height:300,thickness:Number($('thickness').value),material:'plywood',grain:'x',defects:[]});
  renderInventory(); stale();
});
$('apply-json').addEventListener('click', () => {
  try {
    const boards = JSON.parse($('inventory-json').value);
    if (!Array.isArray(boards) || boards.length > 6 || boards.some((b) => !b || typeof b !== 'object' || !Array.isArray(b.defects) || !Number.isFinite(b.width) || !Number.isFinite(b.height))) throw new Error('Enter an array of at most six boards, each with numeric width/height and a defects array.');
    state.request.boards = boards; state.defects.clear(); renderInventory(); stale(); document.querySelector('.advanced').open = false;
  } catch (error) { showError(error.message); }
});
$('download').addEventListener('click', () => { if (state.result) download(JSON.stringify(state.result,null,2),'secondshape-proof.json','application/json'); });
$('download-csv').addEventListener('click', () => {
  if (!state.result) return;
  const cell = (value) => '"' + String(value).replaceAll('"','""') + '"';
  const rows = [['part_id','board_id','x_mm','y_mm','width_mm','height_mm','rotated'], ...state.result.placements.map((p) => [p.part_id,p.board_id,p.x,p.y,p.width,p.height,p.rotated])];
  download(rows.map((r) => r.map(cell).join(',')).join('\n'),'secondshape-cut-list.csv','text/csv');
});
$('verify').addEventListener('click', async () => {
  if (!state.result) return;
  $('verify').disabled = true;
  const revision = state.revision;
  $('verify-status').textContent = 'Rechecking exported coordinates with Python…';
  try {
    const response = await fetch('/api/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(state.result)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Verification request failed.');
    if (revision === state.revision) $('verify-status').textContent = data.valid ? `Verified again. Input fingerprint ${state.result.input_fingerprint.slice(0,16)}…` : 'Verification failed. Inspect the proof before using this layout.';
  } catch (error) { $('verify-status').textContent = error.message; }
  finally { if (revision === state.revision) $('verify').disabled = false; }
});
loadExample();
