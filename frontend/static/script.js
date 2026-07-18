/* teamColors, premTeams, getInitials, setCrest, runIntro come from common.js */

let selectedTeams = [];
let probabilityChart = null;

document.addEventListener('DOMContentLoaded', () => {
    runIntro();
    initApp();
});

/* ==========================================================================
   MAIN APP
   ========================================================================== */
function initApp() {
    const grid = document.getElementById('teamGrid');
    const predictBtn = document.getElementById('predictBtn');
    const selectionArea = document.getElementById('selectionArea');
    const resultArea = document.getElementById('resultArea');
    const loading = document.getElementById('loading');
    const resetBtn = document.getElementById('resetBtn');

    premTeams.forEach(team => {
        const div = document.createElement('div');
        div.className = 'team';
        div.style.setProperty('--team-color', teamColors[team]);

        const img = document.createElement('img');
        setCrest(img, team);

        const name = document.createElement('span');
        name.className = 'team-name';
        name.textContent = team;

        div.appendChild(img);
        div.appendChild(name);

        div.addEventListener('click', () => toggleTeamSelection(team, div));
        grid.appendChild(div);
    });

    const popupModal = document.getElementById('popupModal');
    const modalContent = popupModal.querySelector('.modal-content');
    const modalIcon = document.getElementById('modalIcon');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalCloseBtn = document.getElementById('modalCloseBtn');

    modalCloseBtn.addEventListener('click', hideModal);

    function updatePredictBtn() {
        predictBtn.disabled = selectedTeams.length !== 2;
        if (selectedTeams.length === 0) {
            predictBtn.innerHTML = '<i class="fas fa-mouse-pointer"></i> Select Home Team';
        } else if (selectedTeams.length === 1) {
            predictBtn.innerHTML = '<i class="fas fa-mouse-pointer"></i> Select Away Team';
        } else {
            predictBtn.innerHTML = '<i class="fas fa-bolt"></i> Analyze Matchup';
        }
    }

    function renderVenuePills() {
        document.querySelectorAll('.team').forEach(el => {
            const existing = el.querySelector('.venue-pill');
            if (existing) existing.remove();
        });
        document.querySelectorAll('.team.selected').forEach(el => {
            const team = el.querySelector('.team-name').textContent;
            const idx = selectedTeams.indexOf(team);
            if (idx === -1) return;
            const pill = document.createElement('span');
            pill.className = `venue-pill ${idx === 0 ? 'home' : 'away'}`;
            pill.textContent = idx === 0 ? 'HOME' : 'AWAY';
            el.appendChild(pill);
        });
    }

    function toggleTeamSelection(team, element) {
        if (selectedTeams.includes(team)) {
            selectedTeams = selectedTeams.filter(t => t !== team);
            element.classList.remove('selected');
            gsap.fromTo(element, { scale: 1 }, { scale: 1, duration: 0.2 });
        } else if (selectedTeams.length < 2) {
            selectedTeams.push(team);
            element.classList.add('selected');
            gsap.fromTo(element, { scale: 0.94 }, { scale: 1, duration: 0.35, ease: 'back.out(2)' });
        } else {
            showModal("Limit Reached", "You can only select two teams for simulation.", "warning");
            return;
        }
        renderVenuePills();
        updatePredictBtn();
    }

    predictBtn.addEventListener('click', async () => {
        if (selectedTeams.length !== 2) {
            showModal("Action Required", "Please select exactly two teams to run the analysis.", "info");
            return;
        }

        gsap.to(selectionArea, { opacity: 0, y: -10, duration: 0.3, onComplete: () => {
            selectionArea.classList.add('hidden');
            loading.classList.remove('hidden');
            gsap.fromTo(loading, { opacity: 0 }, { opacity: 1, duration: 0.3 });
        }});

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ team1: selectedTeams[0], team2: selectedTeams[1] })
            });
            const data = await response.json();

            if (!response.ok) {
                showModal("Prediction Unavailable", data.error || "The server could not make a prediction for this matchup.", "warning");
                resetUI();
                return;
            }

            await new Promise(r => setTimeout(r, 1100));
            displayResults(data);
        } catch (error) {
            showModal("Connection Error", "Error connecting to prediction server. Please try again.", "error");
            resetUI();
        }
    });

    function displayResults(data) {
        loading.classList.add('hidden');
        resultArea.classList.remove('hidden');

        setCrest(document.getElementById('team1Image'), selectedTeams[0]);
        setCrest(document.getElementById('team2Image'), selectedTeams[1]);
        document.getElementById('team1NameText').textContent = selectedTeams[0];
        document.getElementById('team2NameText').textContent = selectedTeams[1];

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
            resultDiv.innerHTML = `Our model predicts a <strong>${outcome}</strong> for ${selectedTeams[0]} (home) with <strong>${confidence}%</strong> confidence.`;
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

        probabilityChart = renderProbabilityChart(
            document.getElementById('probabilityChart'), probs, probabilityChart);

        const tl = gsap.timeline();
        tl.fromTo("#resultArea", { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.7, ease: "power3.out" })
          .fromTo(".insight-card", { y: 16, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, stagger: 0.1, ease: "back.out(1.4)" }, "-=0.35");
    }

    resetBtn.addEventListener('click', resetUI);

    function resetUI() {
        selectedTeams = [];
        document.querySelectorAll('.team').forEach(t => t.classList.remove('selected'));
        renderVenuePills();
        updatePredictBtn();

        gsap.to(resultArea, { opacity: 0, scale: 0.96, duration: 0.35, onComplete: () => {
            resultArea.classList.add('hidden');
            loading.classList.add('hidden');
            selectionArea.classList.remove('hidden');
            gsap.fromTo(selectionArea, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.45 });
        }});
    }

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
