document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const dropzoneContent = document.getElementById('dropzoneContent');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const btnRemoveImage = document.getElementById('btnRemoveImage');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    
    const confSlider = document.getElementById('confSlider');
    const confValueDisplay = document.getElementById('confValueDisplay');
    const btnAnalyze = document.getElementById('btnAnalyze');
    const spinner = document.getElementById('spinner');

    const emptyState = document.getElementById('emptyState');
    const resultsContainer = document.getElementById('resultsContainer');

    const metricTotalBeans = document.getElementById('metricTotalBeans');
    const metricDefectTypes = document.getElementById('metricDefectTypes');
    const metricAvgConfidence = document.getElementById('metricAvgConfidence');

    const annotatedImage = document.getElementById('annotatedImage');
    const originalImage = document.getElementById('originalImage');
    const classSummaryTags = document.getElementById('classSummaryTags');
    const detectionsTableBody = document.getElementById('detectionsTableBody');

    const tabBtns = document.querySelectorAll('.tab-btn');

    let selectedFile = null;

    // Confidence Slider Update
    confSlider.addEventListener('input', (e) => {
        confValueDisplay.textContent = `${e.target.value}%`;
    });

    // File Input Selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // Drag & Drop Events
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files && dt.files[0]) {
            handleFileSelect(dt.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file (JPG, PNG, WEBP, etc.)');
            return;
        }

        selectedFile = file;
        fileNameDisplay.innerHTML = `<i class="fa-solid fa-file-image"></i> ${file.name}`;

        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            dropzoneContent.classList.add('hidden');
            previewContainer.classList.remove('hidden');
            btnAnalyze.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    // Remove Selected Image
    btnRemoveImage.addEventListener('click', (e) => {
        e.stopPropagation();
        resetFileInput();
    });

    function resetFileInput() {
        selectedFile = null;
        fileInput.value = '';
        imagePreview.src = '';
        dropzoneContent.classList.remove('hidden');
        previewContainer.classList.add('hidden');
        btnAnalyze.disabled = true;
    }

    // Tab Switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const targetId = btn.dataset.target;
            document.querySelectorAll('.view-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Analyze Image API Call
    btnAnalyze.addEventListener('click', async () => {
        if (!selectedFile) return;

        setLoadingState(true);

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('confidence', (confSlider.value / 100).toString());

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Failed to complete analysis');
            }

            const data = await response.json();
            renderResults(data);

        } catch (err) {
            alert(`Analysis Error: ${err.message}`);
        } finally {
            setLoadingState(false);
        }
    });

    function setLoadingState(isLoading) {
        btnAnalyze.disabled = isLoading;
        if (isLoading) {
            btnAnalyze.querySelector('.btn-text').classList.add('hidden');
            spinner.classList.remove('hidden');
        } else {
            btnAnalyze.querySelector('.btn-text').classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    }

    // Render Detection Results
    function renderResults(data) {
        emptyState.classList.add('hidden');
        resultsContainer.classList.remove('hidden');

        // Metrics
        metricTotalBeans.textContent = data.total_detections;
        const defectTypesCount = Object.keys(data.class_counts || {}).length;
        metricDefectTypes.textContent = defectTypesCount;

        let avgConf = 0;
        if (data.detections && data.detections.length > 0) {
            const sumConf = data.detections.reduce((acc, d) => acc + d.confidence, 0);
            avgConf = Math.round((sumConf / data.detections.length) * 100);
        }
        metricAvgConfidence.textContent = `${avgConf}%`;

        // Images
        annotatedImage.src = `${data.annotated_image_url}?t=${Date.now()}`;
        originalImage.src = `${data.original_image_url}?t=${Date.now()}`;

        // Class Summary Badges
        classSummaryTags.innerHTML = '';
        if (data.class_counts && Object.keys(data.class_counts).length > 0) {
            for (const [cls, count] of Object.entries(data.class_counts)) {
                const badge = document.createElement('div');
                badge.className = 'badge';
                badge.innerHTML = `
                    <span>${cls}</span>
                    <span class="badge-count">${count}</span>
                `;
                classSummaryTags.appendChild(badge);
            }
        } else {
            classSummaryTags.innerHTML = '<span class="text-muted" style="font-size:0.85rem">No defect classes detected</span>';
        }

        // Detections Table
        detectionsTableBody.innerHTML = '';
        if (data.detections && data.detections.length > 0) {
            data.detections.forEach((det, idx) => {
                const row = document.createElement('tr');
                const bboxStr = det.bbox ? `[${det.bbox.join(', ')}]` : 'N/A';
                const yoloInfo = det.yolo_confidence ? `<span style="font-size:0.75rem; color:var(--text-muted); margin-left:4px;">(YOLO: ${Math.round(det.yolo_confidence * 100)}%)</span>` : '';
                row.innerHTML = `
                    <td><strong>${idx + 1}</strong></td>
                    <td><span class="badge" style="font-size:0.75rem">${det.class}</span></td>
                    <td><strong>${det.confidence_percent}</strong> ${yoloInfo}</td>
                    <td><code>${bboxStr}</code></td>
                `;
                detectionsTableBody.appendChild(row);
            });
        } else {
            detectionsTableBody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align:center; color: var(--text-muted); padding: 1.5rem;">
                        No coffee bean defects detected at this confidence threshold. Try lowering the threshold slider.
                    </td>
                </tr>
            `;
        }
    }
});
