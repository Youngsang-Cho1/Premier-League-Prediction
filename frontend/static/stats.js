/* teamColors, getInitials, setCrest, runIntro come from common.js */

document.addEventListener('DOMContentLoaded', () => {
    runIntro();
    initStats();
});

/* ==========================================================================
   STATS APP
   ========================================================================== */
async function initStats() {
    try {
        STATS = await (await fetch('/api/stats')).json();
    } catch (e) {
        document.getElementById('statStrip').innerHTML =
            '<p style="color:rgba(255,255,255,0.6)">Stats unavailable right now.</p>';
        return;
    }

    renderKpis();
    renderCharts();
    renderTable();
    renderPredictions();

    if (skipMotion()) return;
    gsap.fromTo('.stat-tile', { y: 16, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, stagger: 0.08, ease: 'back.out(1.4)' });
    gsap.fromTo('.chart-card, .table-card', { y: 20, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, stagger: 0.1, delay: 0.2, ease: 'power3.out' });
}

function renderKpis() {
    const strip = document.getElementById('statStrip');
    STATS.kpis.forEach(k => {
        const tile = document.createElement('div');
        tile.className = 'stat-tile';
        tile.innerHTML = `
            <div class="stat-value">${k.value}</div>
            <div class="stat-label">${k.label}</div>
            <span class="stat-delta ${k.trend}">${k.delta}</span>
        `;
        strip.appendChild(tile);
    });
}

function renderCharts() {
    // Accuracy by season (real backtest, not gameweeks)
    const trend = STATS.season_trend;
    new Chart(document.getElementById('accuracyChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: trend.map(t => t.season),
            datasets: [{
                data: trend.map(t => +(t.model_acc * 100).toFixed(1)),
                borderColor: '#d3a0da',
                backgroundColor: 'rgba(211, 160, 218, 0.18)',
                borderWidth: 2.5,
                pointBackgroundColor: '#d3a0da',
                pointBorderColor: '#150018',
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.35,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: 'rgba(255, 255, 255, 0.55)', font: { size: 11 } }, grid: { color: 'rgba(255, 255, 255, 0.06)' } },
                y: {
                    ticks: { color: 'rgba(255, 255, 255, 0.55)', font: { size: 11 }, callback: v => v + '%' },
                    grid: { color: 'rgba(255, 255, 255, 0.06)' },
                    suggestedMin: 40, suggestedMax: 70
                }
            }
        }
    });

    // Model vs market by RPS (lower is better) — our real headline metric
    const mc = STATS.market_compare;
    new Chart(document.getElementById('marketChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: mc.seasons,
            datasets: [
                { label: 'Model', data: mc.model_rps, borderColor: '#d3a0da',
                  backgroundColor: 'rgba(211,160,218,0.12)', borderWidth: 2.5,
                  pointRadius: 3, tension: 0.3, fill: false },
                { label: 'Market', data: mc.odds_rps, borderColor: 'rgba(255,255,255,0.5)',
                  borderWidth: 2, borderDash: [5, 4], pointRadius: 3, tension: 0.3, fill: false }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: 'rgba(255,255,255,0.75)', usePointStyle: true, font: { size: 11 } } },
                tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(4)} RPS` } }
            },
            scales: {
                x: { ticks: { color: 'rgba(255, 255, 255, 0.55)', font: { size: 10 } }, grid: { display: false } },
                y: { ticks: { color: 'rgba(255, 255, 255, 0.55)', callback: v => v.toFixed(2) },
                     grid: { color: 'rgba(255, 255, 255, 0.06)' } }
            }
        }
    });
}

function renderTable() {
    const sub = document.getElementById('xpointsSub');
    if (sub && STATS.xpoints.season) {
        sub.textContent = `Actual points vs. model-expected points — ${STATS.xpoints.season} season`;
    }
    const body = document.getElementById('xpointsBody');
    STATS.xpoints.table.forEach((row, i) => {
        const diff = row.diff;
        const diffClass = diff > 0.25 ? 'pos' : diff < -0.25 ? 'neg' : 'even';
        const sign = diff > 0 ? '+' : '';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="num rank">${i + 1}</td>
            <td><div class="team-cell"><img alt=""><span>${row.team}</span></div></td>
            <td class="num">${row.played}</td>
            <td class="num">${row.points}</td>
            <td class="num">${row.xpoints.toFixed(1)}</td>
            <td class="num"><span class="diff-pill ${diffClass}">${sign}${diff.toFixed(1)}</span></td>
        `;
        setCrest(tr.querySelector('.team-cell img'), row.team);
        body.appendChild(tr);
    });
}

function renderPredictions() {
    const log = document.getElementById('predLog');
    const preds = STATS.recent_predictions || [];
    if (!preds.length) {
        log.innerHTML = '<p style="color:rgba(255,255,255,0.5);padding:16px 0">No recent predictions to show.</p>';
        return;
    }
    preds.forEach(p => {
        const row = document.createElement('div');
        row.className = 'pred-row';
        row.innerHTML = `
            <div class="pred-fixture">
                <span class="fx-teams">${p.home} vs ${p.away}</span>
                <span class="fx-sub">${p.date} &middot; Picked ${p.pick} (${p.conf}%)</span>
            </div>
            <div class="pred-score">FT ${p.score}</div>
            <div class="pred-outcome-pill ${p.hit ? 'hit' : 'miss'}">${p.hit ? 'Hit' : 'Miss'}</div>
        `;
        log.appendChild(row);
    });
}
