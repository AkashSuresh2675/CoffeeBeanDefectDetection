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
    const effnetConfSlider = document.getElementById('effnetConfSlider');
    const effnetConfValueDisplay = document.getElementById('effnetConfValueDisplay');
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

    // Confidence Sliders Update
    confSlider.addEventListener('input', (e) => {
        confValueDisplay.textContent = `${e.target.value}%`;
    });

    if (effnetConfSlider) {
        effnetConfSlider.addEventListener('input', (e) => {
            effnetConfValueDisplay.textContent = `${e.target.value}%`;
        });
    }

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

        // Invalidate previous analysis
        clearCurrentAnalysis();
        emptyState.classList.remove('hidden');
        resultsContainer.classList.add('hidden');

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

        clearCurrentAnalysis();
        emptyState.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
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

        let currentDetections = [];
        let chartInstance = null;

        const metricConfirmed = document.getElementById('metricConfirmed');
        const metricUncertain = document.getElementById('metricUncertain');
        const metricProcessingTime = document.getElementById('metricProcessingTime');

        const infoYoloThresh = document.getElementById('infoYoloThresh');
        const infoEffnetThresh = document.getElementById('infoEffnetThresh');
        const infoSampleName = document.getElementById('infoSampleName');

        const tableSearchInput = document.getElementById('tableSearchInput');
        const tableStatusFilter = document.getElementById('tableStatusFilter');
        const tableSortSelect = document.getElementById('tableSortSelect');
        const btnResetFilters = document.getElementById('btnResetFilters');
        const btnExportCsv = document.getElementById('btnExportCsv');

        // Reset file selection clear current detections
        function clearCurrentAnalysis() {
            currentDetections = [];
            if (chartInstance) {
                chartInstance.destroy();
                chartInstance = null;
            }
        }

        // Analyze Image API Call
        btnAnalyze.addEventListener('click', async () => {
            if (!selectedFile) return;

            setLoadingState(true);
            const startTime = performance.now();

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('confidence', (confSlider.value / 100).toString());
            if (effnetConfSlider) {
                formData.append('effnet_confidence', (effnetConfSlider.value / 100).toString());
            }

            try {
                const response = await fetch('/predict', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.error || 'Failed to complete analysis');
                }

                const elapsedMs = Math.round(performance.now() - startTime);
                const data = await response.json();
                renderResults(data, elapsedMs);

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
        function renderResults(data, elapsedMs) {
            emptyState.classList.add('hidden');
            resultsContainer.classList.remove('hidden');

            currentDetections = data.detections || [];

            // 1. Four Compact Stat Cards
            const totalCount = data.total_detections || 0;
            const uncertainCount = currentDetections.filter(d => d.is_uncertain === true).length;
            const confirmedCount = totalCount - uncertainCount;

            metricTotalBeans.textContent = totalCount;
            if (metricConfirmed) metricConfirmed.textContent = confirmedCount;
            if (metricUncertain) metricUncertain.textContent = uncertainCount;
            if (metricProcessingTime) {
                metricProcessingTime.textContent = elapsedMs >= 1000 ? `${(elapsedMs / 1000).toFixed(2)}s` : `${elapsedMs} ms`;
            }

            // 2. Hybrid Model Info Panel Values
            if (infoYoloThresh) infoYoloThresh.textContent = `${confSlider.value}%`;
            if (infoEffnetThresh && effnetConfSlider) infoEffnetThresh.textContent = `${effnetConfSlider.value}%`;
            if (infoSampleName) infoSampleName.textContent = selectedFile ? selectedFile.name : 'Unknown';

            // 3. Images
            annotatedImage.src = `${data.annotated_image_url}?t=${Date.now()}`;
            originalImage.src = `${data.original_image_url}?t=${Date.now()}`;

            // 4. Render Predicted-Class Distribution Chart (Chart.js)
            renderDistributionChart(currentDetections);

            // 5. Class Summary Badges
            renderSummaryBadges(data.class_counts);

            // 6. Reset filters and populate table
            resetTableFilters();
            renderFilteredTable();

            // 7. Save to sessionStorage for Analysis Dashboard page
            try {
                sessionStorage.setItem('coffeeAnalysis', JSON.stringify({
                    data: data,
                    elapsedMs: elapsedMs,
                    yoloThresh: confSlider ? confSlider.value : '25',
                    effnetThresh: effnetConfSlider ? effnetConfSlider.value : '50',
                    sampleName: selectedFile ? selectedFile.name : 'Sample'
                }));
            } catch (e) {
                console.warn('Could not save to sessionStorage:', e);
            }

            // 8. Show View Dashboard button
            const btnViewDashboard = document.getElementById('btnViewDashboard');
            if (btnViewDashboard) {
                btnViewDashboard.classList.remove('hidden');
            }
        }

        // Distribution Chart Rendering
        function renderDistributionChart(detections) {
            const chartCanvas = document.getElementById('distributionChart');
            if (!chartCanvas) return;

            if (chartInstance) {
                chartInstance.destroy();
                chartInstance = null;
            }

            // Count per class, separating confirmed and uncertain consistently
            const classMap = {};
            detections.forEach(det => {
                const cls = det.effnet_class || det.class;
                if (!classMap[cls]) {
                    classMap[cls] = { confirmed: 0, uncertain: 0 };
                }
                if (det.is_uncertain) {
                    classMap[cls].uncertain += 1;
                } else {
                    classMap[cls].confirmed += 1;
                }
            });

            const labels = Object.keys(classMap);
            const confirmedData = labels.map(l => classMap[l].confirmed);
            const uncertainData = labels.map(l => classMap[l].uncertain);

            const ctx = chartCanvas.getContext('2d');
            chartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels.length > 0 ? labels : ['No Detections'],
                    datasets: [
                        {
                            label: 'Confirmed',
                            data: labels.length > 0 ? confirmedData : [0],
                            backgroundColor: 'rgba(112, 196, 154, 0.7)',
                            borderColor: '#70C49A',
                            borderWidth: 1,
                            borderRadius: 4
                        },
                        {
                            label: 'Uncertain',
                            data: labels.length > 0 ? uncertainData : [0],
                            backgroundColor: 'rgba(230, 160, 75, 0.7)',
                            borderColor: '#E6A04B',
                            borderWidth: 1,
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#B8A495',
                                font: { family: 'Outfit', size: 11 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                footer: (items) => {
                                    let sum = 0;
                                    items.forEach(i => sum += i.raw);
                                    return `Total for class: ${sum}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            stacked: true,
                            ticks: { color: '#B8A495', font: { family: 'Outfit', size: 10 } },
                            grid: { color: 'rgba(212, 163, 115, 0.08)' }
                        },
                        y: {
                            stacked: true,
                            beginAtZero: true,
                            ticks: { color: '#B8A495', precision: 0, font: { family: 'Outfit', size: 10 } },
                            grid: { color: 'rgba(212, 163, 115, 0.08)' }
                        }
                    }
                }
            });
        }

        // Summary Badges
        function renderSummaryBadges(classCounts) {
            classSummaryTags.innerHTML = '';
            if (classCounts && Object.keys(classCounts).length > 0) {
                for (const [cls, count] of Object.entries(classCounts)) {
                    const badge = document.createElement('div');
                    const isUncertain = cls.startsWith('Uncertain');
                    badge.className = `badge ${isUncertain ? 'badge-uncertain' : ''}`;
                    if (isUncertain) {
                        badge.style.background = 'rgba(230, 126, 34, 0.15)';
                        badge.style.borderColor = 'rgba(230, 126, 34, 0.4)';
                        badge.style.color = '#e67e22';
                    }
                    badge.innerHTML = `
                        <span>${cls}</span>
                        <span class="badge-count">${count}</span>
                    `;
                    classSummaryTags.appendChild(badge);
                }
            } else {
                classSummaryTags.innerHTML = '<span class="text-muted" style="font-size:0.85rem">No defect classes detected</span>';
            }
        }

        // Table Filtering & Sorting
        function getFilteredDetections() {
            let list = [...currentDetections];

            // Search filter: Strictly matches predicted class name (e.g. 'black' matches 'BLACK' and 'Uncertain (BLACK)')
            const searchVal = (tableSearchInput ? tableSearchInput.value : '').trim().toLowerCase();
            if (searchVal) {
                list = list.filter(d => {
                    const predClass = (d.effnet_class || '').toLowerCase();
                    const fullLabel = (d.class || '').toLowerCase();
                    // Matches if search term matches the predicted class name or the display label
                    return predClass.includes(searchVal) || fullLabel.includes(searchVal);
                });
            }

            // Status filter
            const statusVal = tableStatusFilter ? tableStatusFilter.value : 'all';
            if (statusVal === 'confirmed') {
                list = list.filter(d => !d.is_uncertain);
            } else if (statusVal === 'uncertain') {
                list = list.filter(d => d.is_uncertain === true);
            }

            // Sort
            const sortVal = tableSortSelect ? tableSortSelect.value : 'id_asc';
            list.sort((a, b) => {
                if (sortVal === 'id_asc') {
                    return (a.id || 0) - (b.id || 0);
                } else if (sortVal === 'conf_desc') {
                    const cA = a.effnet_confidence !== undefined ? a.effnet_confidence : a.confidence;
                    const cB = b.effnet_confidence !== undefined ? b.effnet_confidence : b.confidence;
                    return cB - cA;
                } else if (sortVal === 'conf_asc') {
                    const cA = a.effnet_confidence !== undefined ? a.effnet_confidence : a.confidence;
                    const cB = b.effnet_confidence !== undefined ? b.effnet_confidence : b.confidence;
                    return cA - cB;
                } else if (sortVal === 'yolo_desc') {
                    return (b.yolo_confidence || 0) - (a.yolo_confidence || 0);
                }
                return 0;
            });

            return list;
        }

        function renderFilteredTable() {
            detectionsTableBody.innerHTML = '';
            const filtered = getFilteredDetections();

            if (filtered.length > 0) {
                filtered.forEach(det => {
                    const row = document.createElement('tr');
                    const bboxStr = (det.bbox && det.bbox.length === 4)
                        ? `[${det.bbox.map(n => Math.round(n)).join(', ')}]`
                        : 'N/A';
                    const effnetPct = det.confidence_percent || `${Math.round((det.effnet_confidence || 0) * 100)}%`;
                    const yoloPct = det.yolo_confidence !== undefined ? `${Math.round(det.yolo_confidence * 100)}%` : 'N/A';
                    const isUncertain = det.is_uncertain === true;

                    const statusBadge = isUncertain
                        ? `<span class="status-badge status-uncertain"><i class="fa-solid fa-circle-question"></i> Uncertain</span>`
                        : `<span class="status-badge status-confirmed"><i class="fa-solid fa-circle-check"></i> Confirmed</span>`;

                    row.innerHTML = `
                        <td><strong>${det.id}</strong></td>
                        <td><span class="class-badge">${det.class}</span></td>
                        <td><strong>${effnetPct}</strong></td>
                        <td><span>${yoloPct}</span></td>
                        <td>${statusBadge}</td>
                        <td class="bbox-cell">${bboxStr}</td>
                    `;
                    detectionsTableBody.appendChild(row);
                });
            } else {
                detectionsTableBody.innerHTML = `
                    <tr>
                        <td colspan="6" style="text-align:center; color: var(--text-muted); padding: 2rem;">
                            <i class="fa-solid fa-filter-circle-xmark" style="font-size:1.5rem; display:block; margin-bottom:0.5rem; color:var(--text-muted);"></i>
                            No matching detections found for the selected filter or search criteria.
                        </td>
                    </tr>
                `;
            }
        }

        function resetTableFilters() {
            if (tableSearchInput) tableSearchInput.value = '';
            if (tableStatusFilter) tableStatusFilter.value = 'all';
            if (tableSortSelect) tableSortSelect.value = 'id_asc';
        }

        // Table Filter Event Listeners
        if (tableSearchInput) tableSearchInput.addEventListener('input', renderFilteredTable);
        if (tableStatusFilter) tableStatusFilter.addEventListener('change', renderFilteredTable);
        if (tableSortSelect) tableSortSelect.addEventListener('change', renderFilteredTable);
        if (btnResetFilters) {
            btnResetFilters.addEventListener('click', () => {
                resetTableFilters();
                renderFilteredTable();
            });
        }

        // Feature 3: Export CSV Button (Separate 9 Columns)
        if (btnExportCsv) {
            btnExportCsv.addEventListener('click', () => {
                if (!currentDetections || currentDetections.length === 0) {
                    alert('No detections available to export. Run an analysis first.');
                    return;
                }

                const headers = [
                    'Detection ID',
                    'Predicted Class',
                    'Classifier Confidence',
                    'YOLO Confidence',
                    'Status',
                    'x1',
                    'y1',
                    'x2',
                    'y2'
                ];

                const rows = currentDetections.map(d => {
                    const id = d.id;
                    const pClass = `"${(d.class || '').replace(/"/g, '""')}"`;
                    const effConf = d.effnet_confidence !== undefined ? Number(d.effnet_confidence).toFixed(4) : Number(d.confidence || 0).toFixed(4);
                    const yoloConf = d.yolo_confidence !== undefined ? Number(d.yolo_confidence).toFixed(4) : '';
                    const status = d.is_uncertain ? 'Uncertain' : 'Confirmed';
                    const bbox = d.bbox || [0, 0, 0, 0];
                    const x1 = bbox[0] !== undefined ? bbox[0] : '';
                    const y1 = bbox[1] !== undefined ? bbox[1] : '';
                    const x2 = bbox[2] !== undefined ? bbox[2] : '';
                    const y2 = bbox[3] !== undefined ? bbox[3] : '';

                    return [id, pClass, effConf, yoloConf, status, x1, y1, x2, y2].join(',');
                });

                const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
                const encodedUri = encodeURI(csvContent);
                const link = document.createElement('a');
                link.setAttribute('href', encodedUri);
                const sampleName = selectedFile ? selectedFile.name.replace(/\.[^/.]+$/, '') : 'sample';
                link.setAttribute('download', `coffee_defect_analysis_${sampleName}.csv`);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            });
        }
});
