'use strict';

/* ─── State ────────────────────────────── */
let _file = null;
let _wcs = null;
let _lang = 'en';

const HI = {
  'gov': 'भारत सरकार | मत्स्य पालन, पशुपालन और डेयरी मंत्रालय',
  'b-name': 'भारत पशुधन AI पोर्टल',
  'b-sub': 'राष्ट्रीय डिजिटल पशुधन मिशन (SIH 2025)',
  'tab_home': 'होम',
  'tab_scan': 'AI स्कैन स्टूडियो',
  'tab_enc': 'विश्वकोश',
  'tab_expert': 'विशेषज्ञ कतार',
  'tab_audit': 'ऑडिट ट्रेल',
  'upload_title': 'कैप्चर और विश्लेषण',
  'drag_text': 'यहाँ फोटो खींचें और छोड़ें',
  'btn_cam': 'कैमरा का उपयोग करें',
};

/* ─── Navigation ───────────────────────── */
function goPage(pageId, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(pageId).classList.add('active');
  
  if (btn) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
  }

  // Load appropriate data if tab requires it
  if (pageId === 'pg-queue') loadQueue();
  if (pageId === 'pg-audit') loadAudit();
}

function toggleLang() {
  _lang = _lang === 'en' ? 'hi' : 'en';
  const opts = document.querySelectorAll('#lang-toggle .opt');
  opts[0].classList.toggle('on', _lang === 'en');
  opts[1].classList.toggle('on', _lang === 'hi');

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (_lang === 'hi' && HI[key]) {
      if (!el.dataset.en) el.dataset.en = el.innerHTML;
      el.innerHTML = HI[key];
    } else {
      if (el.dataset.en) el.innerHTML = el.dataset.en;
    }
  });
}

/* ─── Drag & Drop / Upload ──────────────── */
function initUpload() {
  const drop = document.getElementById('drop-area');
  const inp  = document.getElementById('inp-file');
  if (!drop || !inp) return;

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(e => {
    drop.addEventListener(e, prev);
  });
  drop.addEventListener('dragover', () => drop.classList.add('dragover'));
  drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
  drop.addEventListener('drop', (e) => {
    drop.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  });
  inp.addEventListener('change', function() {
    if (this.files && this.files[0]) handleFile(this.files[0]);
  });
}

function prev(e) {
  e.preventDefault();
  e.stopPropagation();
}

function handleFile(f) {
  if (!f.type.startsWith('image/')) {
    alert('Please upload a valid image file.');
    return;
  }
  _file = f;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('preview-img').src = e.target.result;
    document.getElementById('preview-box').style.display = 'block';
    document.getElementById('drop-area').style.display = 'none';
    document.getElementById('btn-diagnose').disabled = false;
  };
  reader.readAsDataURL(f);
}

function clearUpload() {
  _file = null;
  document.getElementById('inp-file').value = '';
  document.getElementById('preview-img').src = '';
  document.getElementById('preview-box').style.display = 'none';
  document.getElementById('drop-area').style.display = 'block';
  document.getElementById('btn-diagnose').disabled = true;
  
  // Hide results
  document.getElementById('r-results').style.display = 'none';
  document.getElementById('r-empty').style.display = 'block';
}

/* ─── Camera ───────────────────────────── */
// Simplified camera flow for the demo
function startCamera() {
  alert('Camera access would be requested here on a physical device. For now, please upload a photo using the file picker.');
}

/* ─── Diagnostics ──────────────────────── */
async function runDiagnostics() {
  if (!_file) return;

  const btn = document.getElementById('btn-diagnose');
  btn.disabled = true;
  btn.innerHTML = `⏳ <span>Processing...</span>`;

  document.getElementById('r-empty').style.display = 'none';
  document.getElementById('r-results').style.display = 'none';
  document.getElementById('r-loading').style.display = 'block';

  const fd = new FormData();
  fd.append('image', _file);
  fd.append('region', document.getElementById('inp-region').value);
  fd.append('age', document.getElementById('inp-age').value);
  fd.append('color', document.getElementById('inp-color').value);
  fd.append('notes', document.getElementById('inp-notes').value);

  try {
    const res = await fetch('/api/predict', { method: 'POST', body: fd });
    const data = await res.json();
    
    if (!res.ok) throw new Error(data.error || 'Prediction failed');
    
    populateResults(data);
    
    document.getElementById('r-loading').style.display = 'none';
    document.getElementById('r-results').style.display = 'block';

  } catch (err) {
    alert('Error: ' + err.message);
    document.getElementById('r-loading').style.display = 'none';
    document.getElementById('r-empty').style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.innerHTML = `🔬 <span>Run AI Diagnostics</span>`;
  }
}

async function populateResults(data) {
  // Primary Match
  document.getElementById('breed-name').textContent = data.top1_breed;
  // Dynamic Encyclopedia Data
  const enc = data.breed_details || {};
  document.getElementById('breed-category').textContent = enc.category || 'Unknown Category';
  document.getElementById('native-tract').textContent = enc.native_tract || '—';
  document.getElementById('production-yield').textContent = enc.avg_milk_yield || '—';
  
  if (enc.data_status === 'curated') {
    document.getElementById('speciality-display').textContent = enc.speciality || '—';
    document.getElementById('crossbreeding-advisory').textContent = enc.optimal_crossbreeding || '—';
  } else {
    document.getElementById('speciality-display').textContent = 'Profile pending';
    document.getElementById('crossbreeding-advisory').textContent = 'Profile pending. Breeding guidance not yet available for this breed.';
  }

  // Region Heuristic Boost Badge
  const badge = document.getElementById('heuristic-badge');
  if (data.region_boosted) {
    badge.style.display = 'inline-block';
  } else {
    badge.style.display = 'none';
  }

  // Top 3 Bars
  let html = '';
  data.top3.forEach((t) => {
    const pct = Math.round(t.confidence * 100);
    html += `
      <div class="b-row">
        <div class="b-lbl">${t.breed}</div>
        <div class="b-bar-wrap"><div class="b-bar-fill" style="width:0%" data-w="${pct}%"></div></div>
        <div class="b-pct">${pct}%</div>
      </div>
    `;
  });
  document.getElementById('top3-rows').innerHTML = html;
  
  // Trigger bar animation
  setTimeout(() => {
    document.querySelectorAll('.b-bar-fill').forEach(b => {
      b.style.width = b.getAttribute('data-w');
    });
  }, 50);

  // XAI
  document.getElementById('xai-orig').src = data.image_url;
  document.getElementById('xai-heat').src = data.xai_image_url || data.image_url;

  // Audit
  document.getElementById('audit-hash').textContent = data.blockchain_hash || '—';
  if (data.pashu_aadhaar) {
    document.getElementById('audit-uid').textContent = data.pashu_aadhaar;
  }
  if (data.qr_code_url) {
    document.getElementById('audit-qr').src = data.qr_code_url;
  }
}

/* ─── Toasts & Notifications ───────────── */
function showToast(message) {
  let toast = document.getElementById('toast-notification');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-notification';
    toast.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#15803D;color:white;padding:12px 24px;border-radius:4px;box-shadow:0 4px 6px rgba(0,0,0,0.1);z-index:9999;transition:opacity 0.3s;';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.opacity = '0'; }, 3000);
}

/* ─── Data Tables ──────────────────────── */
async function loadQueue() {
  const tbody = document.getElementById('q-tbody');
  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94A3B8;">Loading...</td></tr>`;
  
  try {
    const res = await fetch('/api/history?status=flagged_for_expert&limit=50');
    const data = await res.json();
    
    if (data.scans.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#15803D; font-weight:600;">No scans flagged for expert review!</td></tr>`;
      return;
    }

    let html = '';
    data.scans.forEach(s => {
      html += `
        <tr>
          <td>${s.id}</td>
          <td><img src="${s.image_path.startsWith('/') ? '' : '/static/'}${s.image_path}" style="height:40px; border-radius:4px;"></td>
          <td><b>${s.predicted_breed}</b><br><small>${(s.confidence_score * 100).toFixed(1)}%</small></td>
          <td><small>Reg: ${s.region_input || '-'}<br>Col: ${s.color_input || '-'}</small></td>
          <td><span class="status-badge flagged_for_expert">Needs Review</span></td>
          <td>
            <button class="act-btn verify" onclick="performAction(${s.id}, '/api/verify')">✓ Verify</button>
            <button class="act-btn retrain" onclick="performAction(${s.id}, '/api/retrain')">⚠️ Flag for Retrain</button>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:red;">Error loading queue.</td></tr>`;
  }
}

async function loadAudit() {
  const tbody = document.getElementById('a-tbody');
  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94A3B8;">Loading...</td></tr>`;
  
  try {
    const res = await fetch('/api/history?limit=50');
    const data = await res.json();
    
    if (data.scans.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#94A3B8;">No records found.</td></tr>`;
      return;
    }

    let html = '';
    data.scans.forEach(s => {
      html += `
        <tr>
          <td><small>${new Date(s.timestamp).toLocaleString()}</small></td>
          <td><img src="${s.image_path.startsWith('/') ? '' : '/static/'}${s.image_path}" style="height:40px; border-radius:4px;"></td>
          <td><b>${s.predicted_breed}</b></td>
          <td>${(s.confidence_score * 100).toFixed(1)}%</td>
          <td><span class="status-badge ${s.status}">${s.status.replace(/_/g, ' ')}</span></td>
          <td style="font-family:monospace; font-size:11px; color:#15803D;">${s.blockchain_hash ? s.blockchain_hash.substring(0,20)+'...' : '-'}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:red;">Error loading audit trail.</td></tr>`;
  }
}

async function performAction(id, endpoint) {
  if (!confirm(`Are you sure you want to perform this action on Scan #${id}?`)) return;
  
  try {
    const fd = new FormData();
    fd.append('scan_id', id);
    
    const res = await fetch(endpoint, { method: 'POST', body: fd });
    if (res.ok) {
      showToast('Action successful!');
      loadQueue();
    } else {
      const e = await res.json();
      alert('Failed: ' + (e.error || 'Unknown error'));
    }
  } catch (err) {
    alert('Error performing action: ' + err.message);
  }
}

async function syncToBPA() {
  const btn = document.getElementById('btn-sync-bpa');
  if(btn) btn.disabled = true;
  
  try {
    const res = await fetch('/api/sync', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message);
    } else {
      alert("Sync failed");
    }
  } catch (err) {
    alert('Error syncing: ' + err.message);
  } finally {
    if(btn) btn.disabled = false;
  }
}

async function loadEncyclopedia(searchQuery = '', filterCategory = 'All') {
  const grid = document.getElementById('enc-grid');
  if(!grid) return;
  
  grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding: 40px; color: #64748B;">Loading Encyclopedia...</div>';
  
  try {
    const res = await fetch('/api/encyclopedia');
    const data = await res.json();
    if(!data.success || !data.breeds) throw new Error("Invalid response");
    
    let html = '';
    data.breeds.forEach(b => {
      // Filter logic
      if (filterCategory !== 'All' && !b.category.includes(filterCategory)) return;
      if (searchQuery && !b.breed_name.toLowerCase().includes(searchQuery.toLowerCase()) && !b.native_tract.toLowerCase().includes(searchQuery.toLowerCase())) return;
      
      html += `
        <div class="enc-card" style="background:white; border-radius:8px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,0.05); border:1px solid #E2E8F0;">
          <h3 style="margin:0 0 8px 0; color:#1B365D;">${b.breed_name}</h3>
          <span style="display:inline-block; background:#E0F2FE; color:#0284C7; padding:4px 8px; border-radius:4px; font-size:12px; margin-bottom:12px;">${b.category}</span>
          <div style="font-size:13px; color:#475569; margin-bottom:8px;">
            <b>Native Tract:</b> ${b.native_tract}
          </div>
          <div style="font-size:13px; color:#475569; margin-bottom:8px;">
            <b>Yield:</b> ${b.avg_milk_yield}
          </div>
          <div style="font-size:13px; color:#475569;">
            <b>Traits:</b> ${b.speciality.substring(0,80)}...
          </div>
        </div>
      `;
    });
    
    if (html === '') html = '<div style="grid-column:1/-1; text-align:center; padding: 40px; color: #64748B;">No breeds match your filter.</div>';
    grid.innerHTML = html;
    
  } catch (err) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding: 40px; color: red;">Error loading catalog.</div>`;
    console.error(err);
  }
}

/* ─── Init ─────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initUpload();
});
