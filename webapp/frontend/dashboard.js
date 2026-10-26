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

    let currentDetections = data.detections || [];
    let chartInstance = null;

    // 1. Metric Cards
    const totalCount = data.total_detections || currentDetections.length;
    const uncertainCount = currentDetections.filter(d => d.is_uncertain === true).length;
    const confirmedCount = totalCount - uncertainCount;

    const confirmedPct = totalCount > 0 ? ((confirmedCount / totalCount) * 100).toFixed(1) : '0.0';
    const uncertainPct = totalCount > 0 ? ((uncertainCount / totalCount) * 100).toFixed(1) : '0.0';

    if (metricTotalBeans) metricTotalBeans.textContent = totalCount;
    if (metricConfirmed) metricConfirmed.textContent = confirmedCount;
    if (metricUncertain) metricUncertain.textContent = uncertainCount;
    if (metricProcessingTime) {
        metricProcessingTime.textContent = elapsedMs >= 1000 ? `${(elapsedMs / 1000).toFixed(2)}s` : `${elapsedMs} ms`;
    }

    const metricConfirmedPct = document.getElementById('metricConfirmedPct');
    const metricUncertainPct = document.getElementById('metricUncertainPct');
    if (metricConfirmedPct) metricConfirmedPct.textContent = `${confirmedPct}%`;
    if (metricUncertainPct) metricUncertainPct.textContent = `${uncertainPct}%`;

    // 2. Hybrid Model Info Panel
    if (infoYoloThresh) infoYoloThresh.textContent = `${yoloThresh}%`;
    if (infoEffnetThresh) infoEffnetThresh.textContent = `${effnetThresh}%`;
    if (infoSampleName) infoSampleName.textContent = sampleName;

    // 3. Render Stacked Distribution Chart
    renderSummaryChart(currentDetections);

    // 4. Render Class-Wise Counts & Percentages Table
    renderClassBreakdownTable(currentDetections, totalCount);

    // 5. Render Confidence Summary Metrics
    renderConfidenceSummary(currentDetections);

    function renderSummaryChart(detections) {
        const chartCanvas = document.getElementById('defectSummaryChart');
        if (!chartCanvas || typeof Chart === 'undefined') return;

        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }

        const classMap = {};
        detections.forEach(det => {
            const cls = det.effnet_class || det.class || 'Unknown';
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
                        data: confirmedData.length > 0 ? confirmedData : [0],
                        backgroundColor: '#70C49A',
                        borderColor: 'rgba(112, 196, 154, 0.8)',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: 'Uncertain',
                        data: uncertainData.length > 0 ? uncertainData : [0],
                        backgroundColor: '#E6A04B',
                        borderColor: 'rgba(230, 160, 75, 0.8)',
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
                        position: 'top',
                        labels: {
                            color: '#F2E8DC',
                            font: { family: 'Outfit', size: 11 },
                            boxWidth: 12
                        }
                    },
                    tooltip: {
                        backgroundColor: '#201711',
                        titleColor: '#D6A56F',
                        bodyColor: '#F2E8DC',
                        borderColor: '#453326',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        ticks: { color: '#B09A88', font: { family: 'Outfit', size: 10 } },
                        grid: { display: false }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: { precision: 0, color: '#B09A88', font: { family: 'Outfit', size: 10 } },
                        grid: { color: 'rgba(69, 51, 38, 0.4)' }
                    }
                }
            }
        });
    }

    function renderClassBreakdownTable(detections, total) {
        const tbody = document.getElementById('classBreakdownTableBody');
        const distinctLabel = document.getElementById('distinctCategoriesCount');
        if (!tbody) return;
        tbody.innerHTML = '';

        const classMap = {};
        detections.forEach(det => {
            const cls = det.effnet_class || det.class || 'Unknown';
            if (!classMap[cls]) {
                classMap[cls] = { total: 0, confirmed: 0, uncertain: 0 };
            }
            classMap[cls].total += 1;
            if (det.is_uncertain) {
                classMap[cls].uncertain += 1;
            } else {
                classMap[cls].confirmed += 1;
            }
        });

        const sortedEntries = Object.entries(classMap).sort((a, b) => b[1].total - a[1].total);
        if (distinctLabel) {
            distinctLabel.textContent = `${sortedEntries.length} Unique Categories`;
        }

        if (sortedEntries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 1.5rem;">No defects detected.</td></tr>';
            return;
        }

        sortedEntries.forEach(([cls, stats]) => {
            const sharePct = total > 0 ? ((stats.total / total) * 100).toFixed(1) : '0.0';
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="class-badge">${cls}</span></td>
                <td><strong>${stats.total}</strong></td>
                <td><span style="color: var(--confirmed-color); font-weight: 600;">${stats.confirmed}</span></td>
                <td><span style="color: var(--uncertain-color); font-weight: 600;">${stats.uncertain}</span></td>
                <td>
                    <div class="percent-bar-container">
                        <div class="percent-bar-bg">
                            <div class="percent-bar-fill" style="width: ${sharePct}%;"></div>
                        </div>
                        <span class="percent-text">${sharePct}%</span>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    function renderConfidenceSummary(detections) {
        const elMeanEff = document.getElementById('statMeanEffNet');
        const elMaxEff = document.getElementById('statMaxEffNet');
        const elMinEff = document.getElementById('statMinEffNet');
        const elMeanYolo = document.getElementById('statMeanYolo');
        const elConfMean = document.getElementById('statConfirmedMean');
        const elUncertMean = document.getElementById('statUncertainMean');

        if (!detections || detections.length === 0) return;

        const effConfs = detections.map(d => d.effnet_confidence !== undefined ? d.effnet_confidence : (d.confidence || 0));
        const yoloConfs = detections.map(d => d.yolo_confidence !== undefined ? d.yolo_confidence : 0);
        const confirmedConfs = detections.filter(d => !d.is_uncertain).map(d => d.effnet_confidence !== undefined ? d.effnet_confidence : (d.confidence || 0));
        const uncertainConfs = detections.filter(d => d.is_uncertain).map(d => d.effnet_confidence !== undefined ? d.effnet_confidence : (d.confidence || 0));

        const avg = arr => arr.length > 0 ? (arr.reduce((s, v) => s + v, 0) / arr.length) : 0;
        const max = arr => arr.length > 0 ? Math.max(...arr) : 0;
        const min = arr => arr.length > 0 ? Math.min(...arr) : 0;

        if (elMeanEff) elMeanEff.textContent = `${(avg(effConfs) * 100).toFixed(1)}%`;
        if (elMaxEff) elMaxEff.textContent = `${(max(effConfs) * 100).toFixed(1)}%`;
        if (elMinEff) elMinEff.textContent = `${(min(effConfs) * 100).toFixed(1)}%`;
        if (elMeanYolo) elMeanYolo.textContent = `${(avg(yoloConfs) * 100).toFixed(1)}%`;
        if (elConfMean) elConfMean.textContent = `${(avg(confirmedConfs) * 100).toFixed(1)}%`;
        if (elUncertMean) elUncertMean.textContent = uncertainConfs.length > 0 ? `${(avg(uncertainConfs) * 100).toFixed(1)}%` : 'N/A';
    }
});
