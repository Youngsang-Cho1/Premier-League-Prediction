const teamColors = {
    "Arsenal": "#EF0107", "Liverpool": "#C8102E", "Manchester Utd": "#DA291C",
    "Southampton": "#D71920", "Nott'ham Forest": "#DD2626", "Burnley": "#6C1D45",
    "Sheffield Utd": "#EE3624", "Chelsea": "#034694", "Manchester City": "#6CABDD",
    "Everton": "#274488", "Leicester City": "#437EBF", "Brighton": "#0057B8",
    "Tottenham": "#131F53", "Aston Villa": "#95BFE5", "West Ham": "#7A2652",
    "Crystal Palace": "#1B458F", "Leeds United": "#FFD200", "Newcastle Utd": "#2D2D2D",
    "Fulham": "#000000", "Norwich City": "#FFF200", "Watford": "#FB9106",
    "Wolves": "#FDB913", "Luton Town": "#F78F1E", "Bournemouth": "#DA291C",
    "Brentford": "#E30613", "Sunderland": "#EB172B", "Ipswich Town": "#3A64A3"
};

const premTeams = Object.keys(teamColors).sort();

function getInitials(team) {
    const words = team.replace(/[^A-Za-z ]/g, '').split(' ').filter(Boolean);
    if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
    return words.map(w => w[0]).join('').slice(0, 3).toUpperCase();
}

function setCrest(img, team) {
    const existing = img.parentElement?.querySelector('.crest-fallback');
    if (existing) existing.remove();
    img.style.display = '';
    const normalName = team.replace(/ /g, '-').replace(/'/g, '');
    img.alt = team;
    img.src = `/static/images/${normalName}-logo.png`;
    img.onerror = () => {
        img.onerror = null;
        img.style.display = 'none';
        const fallback = document.createElement('div');
        fallback.className = 'crest-fallback';
        fallback.style.background = `linear-gradient(160deg, ${teamColors[team]}, color-mix(in srgb, ${teamColors[team]} 45%, black))`;
        fallback.textContent = getInitials(team);
        img.insertAdjacentElement('afterend', fallback);
    };
}

let selectedTeams = [];
let probabilityChart = null;

document.addEventListener('DOMContentLoaded', () => {
    runIntro();
    initApp();
});

/* ==========================================================================
   INTRO SEQUENCE
   ========================================================================== */
function runIntro() {
    const introLayer = document.getElementById('introLayer');
    const mainApp = document.getElementById('mainApp');
    const seen = sessionStorage.getItem('xpoints_intro_seen');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function revealApp(animated) {
        introLayer.style.display = 'none';
        mainApp.style.display = 'flex';
        if (animated) {
            gsap.fromTo(mainApp, { opacity: 0, y: 24 },
                { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
                  onInterrupt: () => gsap.set(mainApp, { opacity: 1, y: 0 }) });
        } else {
            gsap.set(mainApp, { opacity: 1, y: 0 });
        }
        // Guarantee visibility even if the tween never completes (throttled tab)
        setTimeout(() => { mainApp.style.opacity = '1'; }, 1000);
        sessionStorage.setItem('xpoints_intro_seen', '1');
    }

    if (seen || reduced) {
        introLayer.remove();
        revealApp(false);
        return;
    }

    gsap.set(mainApp, { y: 24 });

    let skipped = false;
    const tl = gsap.timeline({
        onComplete: () => { if (!skipped) finishIntro(); }
    });

    // Safety net: never let the app get stuck on the intro if the GSAP
    // timeline's onComplete doesn't fire (animation error, tab throttling).
    const introFailsafe = setTimeout(() => { if (!skipped) finishIntro(); }, 3500);

    tl.to('.intro-glow', { opacity: 1, scale: 1, duration: 0.6, ease: 'power2.out' }, 0)
      .to('.intro-crest', { opacity: 1, scale: 1, rotate: 0, duration: 0.6, ease: 'back.out(1.7)' }, 0.05)
      .to('.intro-pre', { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }, 0.35)
      .to('.intro-main span', { opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'power3.out' }, 0.5)
      .to('.intro-line', { width: '160px', duration: 0.45, ease: 'power2.out' }, 0.85)
      .to('.intro-tagline', { opacity: 1, y: 0, duration: 0.45, ease: 'power2.out' }, 0.95)
      .to('.intro-skip', { opacity: 1, duration: 0.3 }, 1.1)
      .to({}, { duration: 0.9 })
      .to(introLayer, { opacity: 0, filter: 'blur(8px)', duration: 0.4, ease: 'power2.in' });

    function finishIntro() {
        if (skipped) return;
        skipped = true;
        clearTimeout(introFailsafe);
        revealApp(true);
    }

    function skipIntro() {
        if (skipped) return;
        skipped = true;
        clearTimeout(introFailsafe);
        tl.kill();
        gsap.set(introLayer, { opacity: 0 });
        revealApp(true);
    }

    introLayer.addEventListener('click', skipIntro);
    window.addEventListener('keydown', skipIntro, { once: true });
}

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
                    backgroundColor: [
                        'rgba(168, 90, 104, 0.85)',
                        'rgba(199, 154, 69, 0.85)',
                        '#38003c'
                    ],
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
                        labels: {
                            color: 'rgba(31, 21, 34, 0.8)',
                            font: { size: 12, weight: 'bold' },
                            padding: 18,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
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
