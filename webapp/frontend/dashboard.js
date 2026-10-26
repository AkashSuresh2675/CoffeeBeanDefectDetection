document.addEventListener('DOMContentLoaded', () => {
    const rawData = sessionStorage.getItem('coffeeAnalysis');
    const emptyState = document.getElementById('dashboardEmptyState');
    const dashboardContainer = document.getElementById('dashboardContainer');

    if (!rawData) {
        if (emptyState) emptyState.classList.remove('hidden');
        if (dashboardContainer) dashboardContainer.classList.add('hidden');
        return;
    }

    let payload;
    try {
        payload = JSON.parse(rawData);
    } catch (e) {
        console.error('Failed to parse coffeeAnalysis from sessionStorage:', e);
        if (emptyState) emptyState.classList.remove('hidden');
        if (dashboardContainer) dashboardContainer.classList.add('hidden');
        return;
    }

    if (!payload || !payload.data) {
        if (emptyState) emptyState.classList.remove('hidden');
        if (dashboardContainer) dashboardContainer.classList.add('hidden');
        return;
    }

    if (emptyState) emptyState.classList.add('hidden');
    if (dashboardContainer) dashboardContainer.classList.remove('hidden');

    const data = payload.data;
    const elapsedMs = payload.elapsedMs || 0;
    const yoloThresh = payload.yoloThresh || '25';
    const effnetThresh = payload.effnetThresh || '50';
    const sampleName = payload.sampleName || 'Uploaded Sample';

    const metricTotalBeans = document.getElementById('metricTotalBeans');
    const metricConfirmed = document.getElementById('metricConfirmed');
    const metricUncertain = document.getElementById('metricUncertain');
    const metricProcessingTime = document.getElementById('metricProcessingTime');

    const infoYoloThresh = document.getElementById('infoYoloThresh');
    const infoEffnetThresh = document.getElementById('infoEffnetThresh');
    const infoSampleName = document.getElementById('infoSampleName');

    const annotatedImage = document.getElementById('annotatedImage');
    const originalImage = document.getElementById('originalImage');
    const tabBtns = document.querySelectorAll('.tab-btn');

    let currentDetections = data.detections || [];
    let chartInstance = null;

    // Tab Switching for Images
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const targetId = btn.dataset.target;
            document.querySelectorAll('.view-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.classList.add('active');
        });
    });

    // 1. Metric Cards
    const totalCount = data.total_detections || currentDetections.length;
    const uncertainCount = currentDetections.filter(d => d.is_uncertain === true).length;
    const confirmedCount = totalCount - uncertainCount;

    if (metricTotalBeans) metricTotalBeans.textContent = totalCount;
    if (metricConfirmed) metricConfirmed.textContent = confirmedCount;
    if (metricUncertain) metricUncertain.textContent = uncertainCount;
    if (metricProcessingTime) {
        metricProcessingTime.textContent = elapsedMs >= 1000 ? `${(elapsedMs / 1000).toFixed(2)}s` : `${elapsedMs} ms`;
    }

    // 2. Hybrid Model Info Panel
    if (infoYoloThresh) infoYoloThresh.textContent = `${yoloThresh}%`;
    if (infoEffnetThresh) infoEffnetThresh.textContent = `${effnetThresh}%`;
    if (infoSampleName) infoSampleName.textContent = sampleName;

    // 3. Image URLs
    if (annotatedImage && data.annotated_image_url) {
        annotatedImage.src = `${data.annotated_image_url}?t=${Date.now()}`;
    }
    if (originalImage && data.original_image_url) {
        originalImage.src = `${data.original_image_url}?t=${Date.now()}`;
    }

    // 4. Render Distribution Chart
    renderDistributionChart(currentDetections);

    // 5. Render Badges
    renderSummaryBadges(data.class_counts);

    // 6. Interactive Table Controls
    const tableSearchInput = document.getElementById('tableSearchInput');
    const tableStatusFilter = document.getElementById('tableStatusFilter');
    const tableSortSelect = document.getElementById('tableSortSelect');
    const btnResetFilters = document.getElementById('btnResetFilters');
    const btnExportCsv = document.getElementById('btnExportCsv');

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
