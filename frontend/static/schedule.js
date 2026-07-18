/* teamColors, getInitials, setCrest, runIntro come from common.js */

document.addEventListener('DOMContentLoaded', () => {
    runIntro();
    initSchedule();
});

/* ==========================================================================
   SCHEDULE APP
   ========================================================================== */
async function initSchedule() {
    const fixtureList = document.getElementById('fixtureList');
    const scheduleArea = document.getElementById('scheduleArea');
    const resultArea = document.getElementById('resultArea');
    const loading = document.getElementById('loading');
    const resetBtn = document.getElementById('resetBtn');
    let probabilityChart = null;

    let feed;
    try {
        feed = await (await fetch('/api/schedule')).json();
    } catch (e) {
        fixtureList.innerHTML = '<p style="color:rgba(255,255,255,0.6);text-align:center;padding:24px">Could not load fixtures.</p>';
        return;
    }

    // During the off-season the FPL feed has no upcoming games, so the API
    // returns the most recent played round instead — label it honestly.
    const banner = document.getElementById('scheduleBanner');
    if (banner) {
        banner.textContent = feed.is_past
            ? 'Off-season — showing the most recent completed round. Live fixtures return when the season starts.'
            : 'Upcoming fixtures — click any match for a model prediction.';
    }

    if (!feed.fixtures || !feed.fixtures.length) {
        fixtureList.innerHTML = '<p style="color:rgba(255,255,255,0.6);text-align:center;padding:24px">No fixtures available right now.</p>';
        return;
    }

    feed.fixtures.forEach(fx => {
        const row = document.createElement('div');
        row.className = 'fixture-row';

        const teamsWrap = document.createElement('div');
        teamsWrap.className = 'fixture-teams';

        [fx.home, fx.away].forEach((team, i) => {
            if (i === 1) {
                const vs = document.createElement('span');
                vs.className = 'fixture-vs';
                vs.textContent = 'VS';
                teamsWrap.appendChild(vs);
            }
            const wrap = document.createElement('div');
            wrap.className = 'fixture-team';
            const img = document.createElement('img');
            setCrest(img, team);
            const name = document.createElement('span');
            name.textContent = team;
            wrap.appendChild(img);
            wrap.appendChild(name);
            teamsWrap.appendChild(wrap);
        });

        const meta = document.createElement('div');
        meta.className = 'fixture-meta';
        meta.innerHTML = `<span class="when">${fx.day} ${fx.date} &middot; ${fx.time}</span>`;

        row.appendChild(teamsWrap);
        row.appendChild(meta);
        row.addEventListener('click', () => runPrediction(fx.home, fx.away));
        fixtureList.appendChild(row);
    });

    async function runPrediction(team1, team2) {
        gsap.to(scheduleArea, { opacity: 0, y: -10, duration: 0.3, onComplete: () => {
            scheduleArea.classList.add('hidden');
            loading.classList.remove('hidden');
            gsap.fromTo(loading, { opacity: 0 }, { opacity: 1, duration: 0.3 });
        }});

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ team1, team2 })
            });
            const data = await response.json();

            if (!response.ok) {
                showModal("Prediction Unavailable", data.error || "The server could not make a prediction for this matchup.", "warning");
                resetUI();
                return;
            }

            await new Promise(r => setTimeout(r, 1100));
            displayResults(data, team1, team2);
        } catch (error) {
            showModal("Connection Error", "Error connecting to prediction server. Please try again.", "error");
            resetUI();
        }
    }

    function displayResults(data, team1, team2) {
        loading.classList.add('hidden');
        resultArea.classList.remove('hidden');

        setCrest(document.getElementById('team1Image'), team1);
        setCrest(document.getElementById('team2Image'), team2);
        document.getElementById('team1NameText').textContent = team1;
        document.getElementById('team2NameText').textContent = team2;

        const scoreTag = document.getElementById('scorelineTag');
        if (data.scoreline) {
            scoreTag.textContent = data.scoreline;
            scoreTag.classList.remove('hidden');
        } else {
            scoreTag.classList.add('hidden');
        }

        const resultDiv = document.getElementById('result');
        const labels = ['Lose', 'Draw', 'Win'];
        const probs = data.probabilities;

        if (data.result === -1) {
            resultDiv.innerHTML = "Insufficient historical data for a confident prediction.";
        } else {
            const outcome = labels[data.result];
            const confidence = (probs[data.result] * 100).toFixed(1);
            resultDiv.innerHTML = `Our model predicts a <strong>${outcome}</strong> for ${team1} (home) with <strong>${confidence}%</strong> confidence.`;
        }

        if (data.insights) {
            document.getElementById('drawRateValue').textContent = data.insights.draw_rate;
            const historyList = document.getElementById('h2hHistoryList');
            historyList.innerHTML = '';
            if (data.insights.history && data.insights.history.length > 0) {
                data.insights.history.forEach(match => {
                    const row = document.createElement('div');
                    row.className = 'h2h-row';
                    row.innerHTML = `
                        <div class="h2h-date">${match.date}</div>
                        <div class="h2h-score">${match.score}</div>
                        <div class="h2h-result-pill ${match.result}">${match.result}</div>
                    `;
                    historyList.appendChild(row);
                });
            } else {
                historyList.innerHTML = '<p style="text-align:center; opacity:0.5; font-size:0.8rem; margin-top:20px;">No recent H2H records found.</p>';
            }
        }

        updateChart(probs);

        const tl = gsap.timeline();
        tl.fromTo("#resultArea", { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.7, ease: "power3.out" })
          .fromTo(".insight-card", { y: 16, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, stagger: 0.1, ease: "back.out(1.4)" }, "-=0.35");
    }

    function updateChart(probs) {
        const ctx = document.getElementById('probabilityChart').getContext('2d');
        if (probabilityChart) probabilityChart.destroy();
        probabilityChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Lose', 'Draw', 'Win'],
                datasets: [{
                    data: probs,
                    backgroundColor: ['rgba(168, 90, 104, 0.85)', 'rgba(199, 154, 69, 0.85)', '#38003c'],
                    borderColor: ['#a85a68', '#c79a45', '#38003c'],
                    borderWidth: 2,
                    hoverOffset: 12
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                animation: { animateRotate: true, animateScale: true, duration: 900, easing: 'easeOutQuart' },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: 'rgba(31, 21, 34, 0.8)', font: { size: 12, weight: 'bold' }, padding: 18, usePointStyle: true }
                    }
                }
            }
        });
    }

    resetBtn.addEventListener('click', resetUI);
    function resetUI() {
        gsap.to(resultArea, { opacity: 0, scale: 0.96, duration: 0.35, onComplete: () => {
            resultArea.classList.add('hidden');
            loading.classList.add('hidden');
            scheduleArea.classList.remove('hidden');
            gsap.fromTo(scheduleArea, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.45 });
        }});
    }

    const popupModal = document.getElementById('popupModal');
    const modalContent = popupModal.querySelector('.modal-content');
    const modalIcon = document.getElementById('modalIcon');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    modalCloseBtn.addEventListener('click', hideModal);

    const iconMap = {
        'error': '<i class="fas fa-exclamation-triangle"></i>',
        'warning': '<i class="fas fa-exclamation-circle"></i>',
        'success': '<i class="fas fa-check-circle"></i>',
        'info': '<i class="fas fa-info-circle"></i>'
    };

    function showModal(title, message, type = 'info') {
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        modalIcon.innerHTML = iconMap[type];
        modalIcon.className = `modal-icon ${type}`;
        popupModal.classList.remove('hidden');
        gsap.to(popupModal, { opacity: 1, duration: 0.3 });
        gsap.fromTo(modalContent, { opacity: 0, scale: 0.85, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: 0.45, ease: 'back.out(1.5)' });
    }

    function hideModal() {
        gsap.to(modalContent, { opacity: 0, scale: 0.85, y: 16, duration: 0.25, ease: 'power2.in' });
        gsap.to(popupModal, { opacity: 0, duration: 0.25, delay: 0.08, onComplete: () => {
            popupModal.classList.add('hidden');
        }});
    }
}
