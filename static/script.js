const teamColors = {
    "Arsenal": "#EF0107", "Liverpool": "#C8102E", "Manchester Utd": "#DA291C",
    "Southampton": "#D71920", "Nott'ham Forest": "#DD2626", "Burnley": "#6C1D45",
    "Sheffield Utd": "#EE3624", "Chelsea": "#034694", "Manchester City": "#6CABDD",
    "Everton": "#274488", "Leicester City": "#437EBF", "Brighton": "#0057B8",
    "Tottenham": "#131F53", "Aston Villa": "#95BFE5", "West Ham": "#7A2652",
    "Crystal Palace": "#1B458F", "Leeds United": "#FFD200", "Newcastle Utd": "#2D2D2D",
    "Fulham": "#000000", "Norwich City": "#FFF200", "Watford": "#FB9106",
    "Wolves": "#FDB913", "Luton Town": "#F78F1E", "Bournemouth": "#DA291C",
    "Brentford": "#E30613"
};

const premTeams = Object.keys(teamColors).sort();

let selectedTeams = [];
let probabilityChart = null;

document.addEventListener('DOMContentLoaded', () => {
    const introLayer = document.getElementById('introLayer');
    const introText = introLayer.querySelector('.intro-text');
    const mainApp = document.getElementById('mainApp');

    // Cinematic Intro Sequence
    const tl = gsap.timeline();
    tl.fromTo(introText, { opacity: 0, scale: 0.9, y: 30 }, { opacity: 1, scale: 1, y: 0, duration: 2, ease: 'power3.out', delay: 0.5 })
      .to(introText, { opacity: 0, scale: 1.1, filter: 'blur(10px)', duration: 1.5, ease: 'power2.in', delay: 3 })
      .to(introLayer, { opacity: 0, duration: 0.5 })
      .set(introLayer, { display: 'none' })
      .set(mainApp, { display: 'block' })
      .to(mainApp, { opacity: 1, y: 0, duration: 1.5, ease: 'power4.out' });

    const grid = document.getElementById('teamGrid');
    const predictBtn = document.getElementById('predictBtn');
    const updateDataBtn = document.getElementById('updateDataBtn');
    const selectionArea = document.getElementById('selectionArea');
    const resultArea = document.getElementById('resultArea');
    const loading = document.getElementById('loading');
    const resetBtn = document.getElementById('resetBtn');
    const toast = document.getElementById('toast');

    // Initialize Team Grid
    premTeams.forEach(team => {
        const div = document.createElement('div');
        div.className = 'team';
        
        const img = document.createElement('img');
        const normalName = team.replace(/ /g, '-').replace(/'/g, '');
        img.src = `/static/images/${normalName}-logo.png`;
        img.onerror = () => img.src = '/static/images/epl-logo.png'; // Fallback
        
        const name = document.createElement('span');
        name.className = 'team-name';
        name.textContent = team;

        div.appendChild(img);
        div.appendChild(name);

        div.addEventListener('click', () => toggleTeamSelection(team, div));
        grid.appendChild(div);
    });

    // Modal Elements
    const popupModal = document.getElementById('popupModal');
    const modalContent = popupModal.querySelector('.modal-content');
    const modalIcon = document.getElementById('modalIcon');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalCloseBtn = document.getElementById('modalCloseBtn');

    modalCloseBtn.addEventListener('click', hideModal);

    function toggleTeamSelection(team, element) {
        if (selectedTeams.includes(team)) {
            selectedTeams = selectedTeams.filter(t => t !== team);
            element.classList.remove('selected');
        } else if (selectedTeams.length < 2) {
            selectedTeams.push(team);
            element.classList.add('selected');
        } else {
            showModal("Limit Reached", "You can only select two teams for simulation.", "warning");
        }
    }

    predictBtn.addEventListener('click', async () => {
        if (selectedTeams.length !== 2) {
            showModal("Action Required", "Please select exactly two teams to run the analysis.", "info");
            return;
        }

        // Transition to loading
        gsap.to(selectionArea, { opacity: 0, duration: 0.3, onComplete: () => {
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

            // Simulate "thinking" time for effect
            await new Promise(r => setTimeout(r, 1500));

            displayResults(data);
        } catch (error) {
            showModal("Connection Error", "Error connecting to prediction server. Please try again.", "error");
            resetUI();
        }
    });

    function displayResults(data) {
        loading.classList.add('hidden');
        resultArea.classList.remove('hidden');

        // Set images and names
        const t1Normal = selectedTeams[0].replace(/ /g, '-').replace(/'/g, '');
        const t2Normal = selectedTeams[1].replace(/ /g, '-').replace(/'/g, '');
        document.getElementById('team1Image').src = `/static/images/${t1Normal}-logo.png`;
        document.getElementById('team2Image').src = `/static/images/${t2Normal}-logo.png`;
        document.getElementById('team1NameText').textContent = selectedTeams[0];
        document.getElementById('team2NameText').textContent = selectedTeams[1];

        const resultDiv = document.getElementById('result');
        const labels = ['Lose', 'Draw', 'Win'];
        const probs = data.probabilities; // [Lose, Draw, Win]

        if (data.result === -1) {
            resultDiv.innerHTML = "Insufficient historical data for a confident prediction.";
        } else {
            const outcome = labels[data.result];
            const confidence = (probs[data.result] * 100).toFixed(1);
            resultDiv.innerHTML = `Our model predicts a <strong>${outcome}</strong> for ${selectedTeams[0]} with <strong>${confidence}%</strong> confidence.`;
        }

        // Chart.js
        updateChart(probs);

        // Animate entrance
        gsap.fromTo("#resultArea", { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.8, ease: "power3.out" });
    }

    function updateChart(probs) {
        const ctx = document.getElementById('probabilityChart').getContext('2d');
        
        if (probabilityChart) {
            probabilityChart.destroy();
        }

        probabilityChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Lose', 'Draw', 'Win'],
                datasets: [{
                    data: probs,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        '#00ff85' // Premier League Green for Win
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)',
                        '#00ff85'
                    ],
                    borderWidth: 2,
                    hoverOffset: 15
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: 'rgba(255, 255, 255, 0.9)',
                            font: { size: 12, weight: 'bold' },
                            padding: 20,
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
        
        gsap.to(resultArea, { opacity: 0, scale: 0.95, duration: 0.4, onComplete: () => {
            resultArea.classList.add('hidden');
            loading.classList.add('hidden');
            selectionArea.classList.remove('hidden');
            gsap.fromTo(selectionArea, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5 });
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
        gsap.fromTo(modalContent, { opacity: 0, scale: 0.8, y: 50 }, { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: 'back.out(1.5)' });
    }

    function hideModal() {
        gsap.to(modalContent, { opacity: 0, scale: 0.8, y: 20, duration: 0.3, ease: 'power2.in' });
        gsap.to(popupModal, { opacity: 0, duration: 0.3, delay: 0.1, onComplete: () => {
            popupModal.classList.add('hidden');
        }});
    }
});
