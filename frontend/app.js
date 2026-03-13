/* PurNi Menu - Purnima & Nitesh */

// Use full URL when opened from file:// (double-click index.html)
const API = (typeof window !== 'undefined' && window.location?.protocol === 'file:')
  ? 'http://127.0.0.1:8000'
  : '';
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MEAL_SLOTS = ['breakfast', 'lunch', 'dinner', 'snack'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function formatDateRange(startDateStr) {
  if (!startDateStr) return null;
  const [y, m, d] = startDateStr.split('-').map(Number);
  if (!y || !m || !d) return null;
  const mon = new Date(y, m - 1, d);
  const sun = new Date(y, m - 1, d + 6);
  return `Mon ${mon.getDate()} ${MONTHS[mon.getMonth()]} - Sun ${sun.getDate()} ${MONTHS[sun.getMonth()]} ${sun.getFullYear()}`;
}

function setWeekLabel(data) {
  const label = document.getElementById('weekLabel');
  if (!label) return;
  label.textContent = data.date_range || formatDateRange(data.start_date) || `Week ${data.week_number}, ${data.year}`;
}

function showError(msg) {
  const label = document.getElementById('weekLabel');
  const retry = document.getElementById('retryBtn');
  if (label) label.textContent = msg || 'Error loading week';
  if (retry) retry.classList.remove('hidden');
}

function hideError() {
  document.getElementById('retryBtn')?.classList.add('hidden');
}

let state = {
  week: null,
  items: {},
  editingCell: null,
  editingItemId: null,
};

// --- API helpers ---
async function api(path, opts = {}) {
  const isGet = !opts.method || opts.method === 'GET';
  const headers = isGet ? {} : { 'Content-Type': 'application/json' };
  const res = await fetch(API + path, {
    headers: { ...headers, ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch (_) {
    throw new Error('Invalid response from server');
  }
}

async function loadCurrentWeek() {
  return api('/api/weeks/current');
}

async function loadWeek(year, weekNumber) {
  return api(`/api/weeks/${year}/${weekNumber}?_=${Date.now()}`);
}

/** Returns current week + items in one call (backend /api/weeks/current now includes items). */
async function loadCurrentWeekFull() {
  return api(`/api/weeks/current?_=${Date.now()}`);
}

async function addItem(weekId, data) {
  return api(`/api/weeks/${weekId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

async function updateItem(itemId, data) {
  return api(`/api/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

async function deleteItem(itemId) {
  return api(`/api/items/${itemId}`, { method: 'DELETE' });
}

async function lookupNutrition(query) {
  return api(`/api/nutrition/lookup?q=${encodeURIComponent(query)}`);
}

// --- UI ---
/** Ensure items from API are arrays per slot (supports multiple foods per meal). */
function normalizeItems(itemsMap) {
  if (!itemsMap) return {};
  const out = {};
  for (const [k, v] of Object.entries(itemsMap)) {
    out[k] = Array.isArray(v) ? v : (v ? [v] : []);
  }
  return out;
}

function renderGrid() {
  const grid = document.getElementById('menuGrid');
  if (!grid || !state.week) return;

  grid.innerHTML = '';

  // Header row: empty + day names
  const headerRow = document.createElement('div');
  headerRow.className = 'cell header';
  headerRow.textContent = '';
  grid.appendChild(headerRow);
  for (const d of DAY_NAMES) {
    const c = document.createElement('div');
    c.className = 'cell header';
    c.textContent = d;
    grid.appendChild(c);
  }

  for (const slot of MEAL_SLOTS) {
    const labelCell = document.createElement('div');
    labelCell.className = 'cell meal-label';
    labelCell.textContent = slot.charAt(0).toUpperCase() + slot.slice(1);
    grid.appendChild(labelCell);

    for (let day = 0; day < 7; day++) {
      const key = `${day}_${slot}`;
      const items = state.items[key] || [];
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.day = day;
      cell.dataset.slot = slot;
      cell.onclick = () => openModal(day, slot);

      if (items.length > 0) {
        const names = items.map(i => escapeHtml(i.food_name)).join(', ');
        cell.innerHTML = `<div class="food">${names}</div>`;
        // #CALORIE_PROTEIN: restore: <div class="stats">${Math.round(totalCal)} cal · ${totalPro.toFixed(1)}g protein</div>
      } else {
        cell.innerHTML = '<span class="text-muted">+ Add</span>';
      }
      grid.appendChild(cell);
    }
  }
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// #CALORIE_PROTEIN - charts logic, restore later
function getDailyTotals() {
  const totals = Array(7).fill(null).map(() => ({ calories: 0, protein: 0 }));
  for (const key of Object.keys(state.items)) {
    const [day] = key.split('_').map(Number);
    const items = state.items[key];
    if (day >= 0 && day < 7 && Array.isArray(items)) {
      for (const it of items) {
        totals[day].calories += it.calories || 0;
        totals[day].protein += it.protein || 0;
      }
    }
  }
  return totals;
}

function renderCharts() {
  if (document.querySelector('.charts.hidden')) return; // Charts hidden for now
  if (typeof Chart === 'undefined') return;
  try {
    const totals = getDailyTotals();
    const labels = DAY_NAMES;
    const calData = totals.map(t => Math.round(t.calories));
    const proteinData = totals.map(t => Math.round(t.protein * 10) / 10);

    const commonOpts = {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: 'rgba(139, 148, 158, 0.2)' }, ticks: { color: '#8b949e' } },
        x: { grid: { display: false }, ticks: { color: '#8b949e' } },
      },
    };

    const calCtx = document.getElementById('calChart')?.getContext('2d');
    if (calCtx) {
      if (window.calChart) window.calChart.destroy();
      window.calChart = new Chart(calCtx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: calData,
          backgroundColor: 'rgba(232, 184, 109, 0.6)',
          borderColor: '#e8b86d',
          borderWidth: 1,
        }],
      },
      options: commonOpts,
    });
  }

  const proteinCtx = document.getElementById('proteinChart')?.getContext('2d');
  if (proteinCtx) {
    if (window.proteinChart) window.proteinChart.destroy();
    window.proteinChart = new Chart(proteinCtx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: proteinData,
          backgroundColor: 'rgba(63, 185, 80, 0.6)',
          borderColor: '#3fb950',
          borderWidth: 1,
        }],
      },
      options: commonOpts,
    });
  }
  } catch (e) {
    console.warn('Charts failed:', e);
  }
}

function openModal(day, slot) {
  state.editingCell = { day, slot };
  state.editingItemId = null;

  const key = `${day}_${slot}`;
  const items = state.items[key] || [];
  const slotName = slot.charAt(0).toUpperCase() + slot.slice(1);
  const dayName = DAY_NAMES[day];
  document.getElementById('modalTitle').textContent = `${dayName} ${slotName}`;
  renderSlotItemsList(items);
  document.getElementById('foodName').value = '';
  const sz = document.getElementById('servingSize'); if (sz) sz.value = '1 serving';
  const cal = document.getElementById('calories'); if (cal) cal.value = '';
  const pro = document.getElementById('protein'); if (pro) pro.value = '';
  document.getElementById('deleteBtn').style.display = 'none';
  document.getElementById('submitBtn').textContent = items.length > 0 ? '+ Add another food' : 'Add food';
  document.getElementById('modal').classList.remove('hidden');
}

function renderSlotItemsList(items) {
  const container = document.getElementById('slotItems');
  if (!container) return;
  if (items.length === 0) {
    container.innerHTML = '<p class="slot-empty">Add bread, butter, milk, etc.</p>';
    container.classList.add('empty');
    return;
  }
  container.classList.remove('empty');
  container.innerHTML = '<p class="slot-header">Foods in this meal:</p>' + items.map(it => `
    <div class="slot-item" data-id="${it.id}">
      <span class="slot-item-name">${escapeHtml(it.food_name)}</span>
      <button type="button" class="slot-item-edit" data-id="${it.id}">Edit</button>
      <button type="button" class="slot-item-delete" data-id="${it.id}">Delete</button>
    </div>
  `).join('');
  // #CALORIE_PROTEIN restore: <span class="slot-item-stats">${Math.round(it.calories)} cal · ${it.protein}g protein</span>
  container.querySelectorAll('.slot-item-edit').forEach(btn => {
    btn.onclick = () => loadItemForEdit(Number(btn.dataset.id));
  });
  container.querySelectorAll('.slot-item-delete').forEach(btn => {
    btn.onclick = () => deleteItemInModal(Number(btn.dataset.id));
  });
}

function loadItemForEdit(itemId) {
  const key = `${state.editingCell.day}_${state.editingCell.slot}`;
  const items = state.items[key] || [];
  const it = items.find(i => i.id === itemId);
  if (!it) return;
  state.editingItemId = itemId;
  document.getElementById('foodName').value = it.food_name;
  const sz = document.getElementById('servingSize'); if (sz) sz.value = it.serving_size || '1 serving';
  const cal = document.getElementById('calories'); if (cal) cal.value = Math.round(it.calories);
  const pro = document.getElementById('protein'); if (pro) pro.value = it.protein ?? '';
  document.getElementById('deleteBtn').style.display = 'inline-block';
  document.getElementById('submitBtn').textContent = 'Update';
}

async function deleteItemInModal(itemId) {
  if (!confirm('Delete this food?')) return;
  try {
    await deleteItem(itemId);
    await loadWeekData();
    const key = `${state.editingCell.day}_${state.editingCell.slot}`;
    const items = state.items[key] || [];
    renderSlotItemsList(items);
    if (state.editingItemId === itemId) {
      state.editingItemId = null;
      document.getElementById('foodName').value = '';
      const sz = document.getElementById('servingSize'); if (sz) sz.value = '1 serving';
      const cal = document.getElementById('calories'); if (cal) cal.value = '';
      const pro = document.getElementById('protein'); if (pro) pro.value = '';
      document.getElementById('deleteBtn').style.display = 'none';
      document.getElementById('submitBtn').textContent = 'Add food';
    }
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  state.editingCell = null;
  state.editingItemId = null;
}

async function saveMeal(e) {
  e.preventDefault();
  const { day, slot } = state.editingCell;
  const foodName = document.getElementById('foodName').value.trim();
  const servingSize = (document.getElementById('servingSize')?.value || '').trim() || '1 serving';
  const calories = parseFloat(document.getElementById('calories')?.value || '0') || 0;
  const protein = parseFloat(document.getElementById('protein')?.value || '0') || 0;
  const addedBy = document.getElementById('editorName').value;

  try {
    if (state.editingItemId) {
      await updateItem(state.editingItemId, { food_name: foodName, serving_size: servingSize, calories, protein });
      closeModal();
      await loadWeekData();
    } else {
      const added = await addItem(state.week.id, {
        day,
        meal_slot: slot,
        food_name: foodName,
        serving_size: servingSize,
        calories,
        protein,
        added_by: addedBy,
      });
      const key = `${day}_${slot}`;
      const prev = state.items[key] || [];
      state.items[key] = [...prev, added];
      // Don't refetch - it was overwriting with stale data and eating previous items
      document.getElementById('foodName').value = '';
      const sz2 = document.getElementById('servingSize'); if (sz2) sz2.value = '1 serving';
      const cal2 = document.getElementById('calories'); if (cal2) cal2.value = '';
      const pro2 = document.getElementById('protein'); if (pro2) pro2.value = '';
      renderSlotItemsList(state.items[key]);
      document.getElementById('submitBtn').textContent = '+ Add another';
      renderGrid();
      renderCharts();
      updateDownloadLink();
    }
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

async function deleteMeal() {
  if (!state.editingItemId) return;
  if (!confirm('Delete this meal?')) return;
  try {
    await deleteItem(state.editingItemId);
    closeModal();
    await loadWeekData();
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// #CALORIE_PROTEIN - lookup, restore when inputs are back
async function doLookup() {
  const cal = document.getElementById('calories');
  const pro = document.getElementById('protein');
  if (!cal || !pro) return;
  const q = document.getElementById('foodName').value.trim();
  if (!q) { alert('Enter a food name first'); return; }
  try {
    const r = await lookupNutrition(q);
    cal.value = Math.round(r.calories);
    pro.value = Math.round(r.protein * 10) / 10;
  } catch (err) {
    alert('Lookup failed: ' + err.message);
  }
}

async function loadWeekData() {
  try {
    if (!state.week) {
      const data = await loadCurrentWeekFull();
      state.week = { id: data.id, year: data.year, week_number: data.week_number };
      state.items = normalizeItems(data.items || {});
      setWeekLabel(data);
      renderGrid();
      renderCharts();
      updateDownloadLink();
      hideError();
      return;
    }
    const data = await loadWeek(state.week.year, state.week.week_number);
    state.items = normalizeItems(data.items || {});
    const dateLabel = data.date_range || formatDateRange(data.start_date) || `Week ${data.week_number}, ${data.year}`;
    document.getElementById('weekLabel').textContent = dateLabel;
    hideError();
    renderGrid();
    renderCharts();
    updateDownloadLink();
  } catch (err) {
    console.error(err);
    showError(err.message || 'Error loading week');
  }
}

function updateDownloadLink() {
  if (!state.week) return;
  const odsBtn = document.getElementById('downloadOds');
  const pdfBtn = document.getElementById('downloadPdf');
  const base = API || window.location.origin;
  const name = `PurNi_Menu_${state.week.year}_W${state.week.week_number}`;
  if (odsBtn) {
    odsBtn.href = `${base}/api/weeks/${state.week.year}/${state.week.week_number}/download/ods`;
    odsBtn.download = `${name}.ods`;
  }
  if (pdfBtn) {
    pdfBtn.href = `${base}/api/menu-pdf/${state.week.year}/${state.week.week_number}?v=${Date.now()}`;
    pdfBtn.download = `${name}.pdf`;
  }
}

/** Programmatic download: fetch file as blob and trigger save. Falls back to direct link if fetch fails. */
async function downloadFile(url, filename) {
  try {
    const res = await fetch(url, { method: 'GET' });
    if (!res.ok) {
      const msg = res.status === 404
        ? '404 – API not found. Stop any other server and run: run.bat or python run.py'
        : `Download failed: ${res.status} ${res.statusText}`;
      throw new Error(msg);
    }
    const blob = await res.blob();
    const a = document.createElement('a');
    const blobUrl = URL.createObjectURL(blob);
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 200);
  } catch (err) {
    console.error(err);
    showError('Download failed: ' + err.message);
    // Fallback: open URL so user can save (popup might be blocked, so try both)
    if (url.startsWith('http')) {
      const w = window.open(url, '_blank', 'noopener');
      if (!w) window.location.href = url;
    }
  }
}

async function gotoWeek(delta) {
  if (!state.week) return;
  try {
    let y = state.week.year;
    let w = state.week.week_number + delta;
    if (w < 1) { w = 52; y--; }
    if (w > 52) { w = 1; y++; }
    const data = await loadWeek(y, w);
    state.week = { id: data.id, year: data.year, week_number: data.week_number };
    state.items = normalizeItems(data.items || {});
    const dateLabel = data.date_range || formatDateRange(data.start_date) || `Week ${data.week_number}, ${data.year}`;
    document.getElementById('weekLabel').textContent = dateLabel;
    hideError();
    renderGrid();
    renderCharts();
    updateDownloadLink();
  } catch (err) {
    console.error(err);
    showError('Error: ' + (err.message || 'Failed to load week'));
  }
}

// --- Init ---
document.getElementById('mealForm').addEventListener('submit', saveMeal);
document.getElementById('deleteBtn').addEventListener('click', deleteMeal);
document.getElementById('cancelBtn').addEventListener('click', closeModal);
document.getElementById('lookupBtn')?.addEventListener('click', doLookup);
document.getElementById('prevWeek').addEventListener('click', () => gotoWeek(-1));
document.getElementById('nextWeek').addEventListener('click', () => gotoWeek(1));
document.getElementById('retryBtn').addEventListener('click', () => loadWeekData());

document.getElementById('downloadOds')?.addEventListener('click', (e) => {
  if (!state.week) { e.preventDefault(); showError('Load a week first'); return; }
  // Let link navigate - href is set by updateDownloadLink; avoids fetch/blob blocking issues
});
document.getElementById('downloadPdf')?.addEventListener('click', (e) => {
  if (!state.week) { e.preventDefault(); showError('Load a week first'); return; }
  // Let link navigate - href is set by updateDownloadLink; avoids fetch/blob blocking issues
});

document.getElementById('modal').addEventListener('click', (e) => {
  if (e.target.id === 'modal') closeModal();
});

loadWeekData();
