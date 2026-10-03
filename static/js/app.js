/**
 * CornShield AI - Frontend Application Controller
 * Handles image capture, test specimens, UI updates, visual segmentation toggle, and field logs.
 */

// Application State
let currentDiagnosis = null;
let currentImageView = 'original';

document.addEventListener('DOMContentLoaded', () => {
  initHealthCheck();
  initUploadListeners();
  loadFieldList();
  loadHistory('all');
});

// 1. Health & Connection Status
async function initHealthCheck() {
  const badge = document.getElementById('connectionBadge');
  const text = document.getElementById('connectionText');
  try {
    const res = await fetch('/health');
    const data = await res.json();
    if (data.status === 'healthy') {
      if (data.cloud_vision_enabled) {
        text.textContent = `Vision AI Active (${data.vision_model.split('/').pop()})`;
        badge.className = 'status-pill status-online';
      } else {
        text.textContent = 'Local CV Diagnostic Engine (Offline)';
        badge.className = 'status-pill status-online';
      }
    }
  } catch (err) {
    text.textContent = 'Server Offline';
    badge.className = 'status-pill';
    badge.style.background = '#fee2e2';
    badge.style.color = '#dc2626';
  }
}

// 2. Drag & Drop and File Input Setup
function initUploadListeners() {
  const dropzone = document.getElementById('dropzone');
  const cameraInput = document.getElementById('cameraInput');
  const fileInput = document.getElementById('fileInput');

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
    }, false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  cameraInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileSelected(e.target.files[0]);
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileSelected(e.target.files[0]);
  });
}

function handleFileSelected(file) {
  if (!file.type.startsWith('image/')) {
    alert('Please select a valid image file (JPEG, PNG).');
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    showPreview(e.target.result);
    uploadAndDiagnose(file);
  };
  reader.readAsDataURL(file);
}

function showPreview(dataUrl) {
  const prompt = document.getElementById('uploadPrompt');
  const previewContainer = document.getElementById('previewContainer');
  const imagePreview = document.getElementById('imagePreview');
  const overlay = document.getElementById('loadingOverlay');

  prompt.style.display = 'none';
  previewContainer.style.display = 'block';
  imagePreview.src = dataUrl;
  overlay.style.display = 'flex';
}

function hidePreviewOverlay() {
  const overlay = document.getElementById('loadingOverlay');
  overlay.style.display = 'none';
}

// 3. Upload & Diagnosis API Call
async function uploadAndDiagnose(file) {
  const activeField = document.getElementById('activeFieldInput').value.trim() || 'Main Field';
  const formData = new FormData();
  formData.append('image', file);
  formData.append('field_id', activeField);

  try {
    const response = await fetch('/api/diagnose', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    renderDiagnosisResult(data, imagePreview.src);
    loadHistory(activeField);
  } catch (err) {
    alert(`Diagnosis error: ${err.message}`);
    document.getElementById('uploadPrompt').style.display = 'block';
    document.getElementById('previewContainer').style.display = 'none';
  } finally {
    hidePreviewOverlay();
  }
}

// 4. One-Click Sample Testing for Judges
async function testSample(sampleId) {
  const activeField = document.getElementById('activeFieldInput').value.trim() || 'North Pivot - Section 4';
  
  // Show specimen thumbnail in preview first
  showPreview(`/api/samples/image/${sampleId === 'tar_spot' ? 'tar_spot_specimen.jpg' : sampleId + '_specimen.jpg'}`);
  
  try {
    const response = await fetch(`/api/samples/test/${sampleId}?field_id=${encodeURIComponent(activeField)}`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Sample test request failed');
    const data = await response.json();
    
    // Set preview image
    const sampleImgUrl = `/api/samples/image/${sampleId === 'tar_spot' ? 'tar_spot_specimen.jpg' : sampleId + '_specimen.jpg'}`;
    renderDiagnosisResult(data, sampleImgUrl);
    loadHistory(activeField);
  } catch (err) {
    alert(`Sample test error: ${err.message}`);
  } finally {
    hidePreviewOverlay();
  }
}

// 5. Render Diagnosis Results to Screen
function renderDiagnosisResult(data, originalImageUrl) {
  currentDiagnosis = data;
  const resultSection = document.getElementById('resultSection');
  resultSection.style.display = 'block';

  const d = data.diagnosis;
  const s = data.severity;
  const t = data.treatment;

  // Title & Pathogen
  document.getElementById('diseaseNameText').textContent = d.disease_name;
  document.getElementById('pathogenText').textContent = `Pathogen: ${t.pathogen}`;

  // Engine badge (Truthful reporting of inference source)
  const engineBadge = document.getElementById('engineBadge');
  if (d.inference_engine && d.inference_engine.startsWith('cloud_vision')) {
    const modelName = d.inference_engine.replace('cloud_vision_', '').split('/').pop();
    engineBadge.textContent = `Cloud Vision AI (${modelName})`;
  } else if (d.inference_engine && d.inference_engine.includes('fallback')) {
    engineBadge.textContent = 'Local CV Fallback (Cloud Offline)';
  } else {
    engineBadge.textContent = 'Local CV Engine (100% Offline)';
  }

  // Confidence
  const confPct = Math.round(d.confidence * 100);
  document.getElementById('confidenceVal').textContent = `${confPct}%`;
  const confBar = document.getElementById('confidenceBar');
  confBar.style.width = `${confPct}%`;
  if (confPct < 70) {
    confBar.style.background = '#d97706';
  } else {
    confBar.style.background = 'linear-gradient(90deg, #22c55e, #15803d)';
  }

  // Reasoning / Visual Traits
  let reasoningStr = d.diagnostic_reasoning || '';
  if (d.visual_symptoms && d.visual_symptoms.length > 0) {
    reasoningStr = `${reasoningStr} Symptoms observed: ${d.visual_symptoms.join(', ')}`;
  }
  document.getElementById('reasoningText').textContent = reasoningStr || 'Characteristic foliar lesions detected.';

  // Calibration Alert (Hedge / Unsure Path)
  const alertBox = document.getElementById('calibrationAlert');
  if (!d.is_confident) {
    alertBox.style.display = 'flex';
    document.getElementById('hedgeReasonText').textContent = d.hedge_reason || 'Confidence is below field threshold.';

    // Differential candidates
    const diffContainer = document.getElementById('differentialsList');
    diffContainer.innerHTML = '';
    if (d.top_candidates && d.top_candidates.length > 0) {
      d.top_candidates.forEach(cand => {
        const chip = document.createElement('span');
        chip.className = 'diff-chip';
        const candProb = Math.round((cand.probability || 0) * 100);
        chip.textContent = `${cand.name || cand.disease_id} (${candProb}%)`;
        diffContainer.appendChild(chip);
      });
    }

    // Retake steps
    const retakeList = document.getElementById('retakeInstructionsList');
    retakeList.innerHTML = '';
    if (d.retake_instructions && d.retake_instructions.length > 0) {
      d.retake_instructions.forEach(step => {
        const li = document.createElement('li');
        li.textContent = step;
        retakeList.appendChild(li);
      });
    }
  } else {
    alertBox.style.display = 'none';
  }

  // Severity metrics
  document.getElementById('severityPctText').textContent = `${s.severity_pct}%`;
  const gradeBadge = document.getElementById('severityGradeBadge');
  gradeBadge.textContent = s.severity_grade;
  gradeBadge.className = 'grade-badge';
  if (s.severity_grade.toLowerCase() === 'early') {
    gradeBadge.classList.add('grade-early');
  } else if (s.severity_grade.toLowerCase() === 'moderate') {
    gradeBadge.classList.add('grade-moderate');
  } else {
    gradeBadge.classList.add('grade-severe');
  }

  // Visual Segmentation viewer
  const imgOriginal = document.getElementById('resultImageOriginal');
  const imgMask = document.getElementById('resultImageMask');
  imgOriginal.src = originalImageUrl;
  imgMask.src = s.segmentation_overlay_b64;
  switchImageView('original');

  // Treatment card fields
  document.getElementById('treatmentText').textContent = t.treatment;
  document.getElementById('activeIngredientsText').textContent = t.active_ingredients;
  document.getElementById('rateText').textContent = t.rate;
  document.getElementById('intervalText').textContent = t.interval;
  document.getElementById('phiText').textContent = t.preharvest_interval;
  document.getElementById('reiText').textContent = t.reentry_interval;
  document.getElementById('costText').textContent = t.estimated_cost_per_acre;
  document.getElementById('safetyNotesText').textContent = t.safety_notes;

  const sourceLink = document.getElementById('sourceLink');
  sourceLink.textContent = t.source_title;
  sourceLink.href = t.source_url;

  // Log confirmation
  document.getElementById('savedFieldTarget').textContent = data.field_id;
  document.getElementById('scanIdDisplay').textContent = `(Scan #${data.scan_id})`;

  // Smooth scroll to results
  resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 6. Switch Image View (Original Photo vs AI Lesion Mask)
function switchImageView(view) {
  currentImageView = view;
  const imgOriginal = document.getElementById('resultImageOriginal');
  const imgMask = document.getElementById('resultImageMask');
  const btnOriginal = document.getElementById('toggleOriginalBtn');
  const btnMask = document.getElementById('toggleMaskBtn');

  if (view === 'original') {
    imgOriginal.style.display = 'block';
    imgMask.style.display = 'none';
    btnOriginal.classList.add('active');
    btnMask.classList.remove('active');
  } else {
    imgOriginal.style.display = 'none';
    imgMask.style.display = 'block';
    btnOriginal.classList.remove('active');
    btnMask.classList.add('active');
  }
}

// 7. Load History & Analytics
async function loadHistory(fieldId) {
  const activeFieldName = document.getElementById('activeFieldName');
  const tableBody = document.getElementById('historyTableBody');
  
  if (fieldId && fieldId !== 'all') {
    activeFieldName.textContent = fieldId;
  } else {
    activeFieldName.textContent = 'All Fields';
  }

  // Load analytics
  loadFieldAnalytics(fieldId === 'all' ? 'North Pivot - Section 4' : fieldId);

  try {
    const url = fieldId && fieldId !== 'all' ? `/api/scans?field_id=${encodeURIComponent(fieldId)}` : '/api/scans';
    const res = await fetch(url);
    const scans = await res.json();

    tableBody.innerHTML = '';
    if (scans.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="7" class="empty-state">No scouting scans recorded yet for this field.</td></tr>';
      return;
    }

    scans.forEach(scan => {
      const row = document.createElement('tr');
      const dateFormatted = scan.timestamp ? scan.timestamp.slice(0, 16).replace('T', ' ') : 'N/A';
      const gradeClass = scan.severity_grade.toLowerCase() === 'early' ? 'badge-success' : (scan.severity_grade.toLowerCase() === 'moderate' ? 'badge-warning' : 'badge-danger');
      const thumb = scan.thumbnail_b64 ? `<img src="${scan.thumbnail_b64}" class="thumb-preview" alt="Scan">` : '<div class="thumb-preview" style="background:#e2e8f0;"></div>';

      row.innerHTML = `
        <td>${thumb}</td>
        <td><small>${dateFormatted}</small></td>
        <td><strong>${scan.field_id}</strong></td>
        <td>${scan.disease_name}</td>
        <td><span class="sample-badge ${gradeClass}">${scan.severity_pct}% (${scan.severity_grade})</span></td>
        <td>${Math.round(scan.confidence * 100)}%</td>
        <td><small>${scan.action_taken || 'Scouted'}</small></td>
      `;
      tableBody.appendChild(row);
    });
  } catch (err) {
    console.error('Failed to load history:', err);
  }
}

async function loadFieldAnalytics(fieldId) {
  try {
    const res = await fetch(`/api/field-analytics?field_id=${encodeURIComponent(fieldId)}`);
    const a = await res.json();
    document.getElementById('fieldTrendText').textContent = a.trend || 'Baseline';
    document.getElementById('fieldTrajectoryDesc').textContent = a.trajectory_description || '';
    document.getElementById('fieldActionRec').textContent = a.action_recommendation || '';
  } catch (err) {
    console.error('Failed to load analytics:', err);
  }
}

async function loadFieldList() {
  const select = document.getElementById('fieldFilterSelect');
  try {
    const res = await fetch('/api/scans');
    const scans = await res.json();
    const fields = new Set(scans.map(s => s.field_id));
    fields.forEach(f => {
      if (f && f !== 'all') {
        const opt = document.createElement('option');
        opt.value = f;
        opt.textContent = f;
        select.appendChild(opt);
      }
    });
  } catch (err) {
    console.error(err);
  }
}

function scrollToHistory() {
  document.getElementById('historySection').scrollIntoView({ behavior: 'smooth' });
}
