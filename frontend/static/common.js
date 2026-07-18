/* Shared across index / stats / schedule pages: team colors, crest loading
   with an initials fallback, and the cinematic intro sequence. */

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

/* True when entrance animations should be skipped: the ?nointro deep-link
   or the user's reduced-motion preference. Pages use this to render content
   immediately instead of fading it in. */
function skipMotion() {
    return new URLSearchParams(location.search).has('nointro')
        || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/* Win/Draw/Lose probability doughnut. Shared so the predict and schedule
   pages always use the same theme-matched colors (Win = lilac, Draw = muted,
   Lose = rose). Destroys any prior chart on the canvas and returns the new
   instance. `probs` is ordered [Lose, Draw, Win]. */
function renderProbabilityChart(canvas, probs, prevChart) {
    if (prevChart) prevChart.destroy();
    return new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Lose', 'Draw', 'Win'],
            datasets: [{
                data: probs,
                backgroundColor: ['#a05a72', '#6f5f80', '#d3a0da'],
                borderColor: 'transparent',
                borderWidth: 0,
                hoverOffset: 8,
                spacing: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            animation: { animateRotate: true, animateScale: false, duration: 800, easing: 'easeOutQuart' },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.75)',
                        font: { size: 12, weight: '600' },
                        padding: 18,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        boxWidth: 8
                    }
                }
            }
        }
    });
}

/* Cinematic intro. Plays once per session; skippable by click/keypress;
   respects prefers-reduced-motion. A failsafe guarantees the app is
   revealed even if the GSAP timeline's onComplete never fires. */
function runIntro() {
    const introLayer = document.getElementById('introLayer');
    const mainApp = document.getElementById('mainApp');
    const displayMode = mainApp.dataset.display || 'block';
    // ?nointro skips the animation (handy when linking straight to a page)
    const noIntro = new URLSearchParams(location.search).has('nointro');
    const seen = noIntro || sessionStorage.getItem('xpoints_intro_seen');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function revealApp(animated) {
        introLayer.style.display = 'none';
        mainApp.style.display = displayMode;
        if (animated) {
            gsap.fromTo(mainApp, { opacity: 0, y: 24 },
                { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
                  onInterrupt: () => gsap.set(mainApp, { opacity: 1, y: 0 }) });
        } else {
            gsap.set(mainApp, { opacity: 1, y: 0 });
        }
        setTimeout(() => { mainApp.style.opacity = '1'; }, 1000);
        sessionStorage.setItem('xpoints_intro_seen', '1');
    }

    if (seen || reduced || !document.querySelector('.intro-main')) {
        if (introLayer) introLayer.remove();
        revealApp(false);
        return;
    }

    gsap.set(mainApp, { y: 24 });

    let skipped = false;
    const tl = gsap.timeline({ onComplete: () => { if (!skipped) finishIntro(); } });
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
