

const premTeams = (['Manchester City', 'Arsenal', 'Liverpool',
    'Aston Villa', 'Tottenham', 'Chelsea', 'Newcastle Utd', 'Manchester Utd', 'West Ham',
    'Crystal Palace', 'Brighton', 'Bournemouth', 'Fulham', 'Wolves', 'Everton', 'Brentford',
    "Nott'ham Forest", 'Luton Town', 'Burnley', 'Sheffield Utd', 'Leicester City', 'Leeds United',
    'Southampton', 'Watford', 'Norwich City'])

let selected = []

const grid = document.getElementById('teamGrid');
const predictBtn = document.getElementById('predictBtn');
const result = document.getElementById('result')

premTeams.forEach(team => {
    const div = document.createElement('div')
    div.classList.add('team')
    div.textContent = team
    div.addEventListener('click', () => {
        if (selected.includes(team)) {
            selected = selected.filter(t => t !== team)
            div.classList.remove('selected')
        }
        else if (selected.length < 2) {
            selected.push(team)
            div.classList.add('selected')
        }
        else if (selected.length > 2) {
            alert('Only two teams can be selected.')
        }
    })
    grid.appendChild(div)
})

predictBtn.addEventListener('click', async() => {
    if (selected.length !== 2) {
        alert('Please select exactly two teams.')
        return;
    }
    const url = '/predict'
    const options = {
        method : 'POST',
        headers : {
            'Content-Type' : 'application/JSON'
        }, 
        body : JSON.stringify({team1 : selected[0], team2: selected[1]})
    }
    const res = await fetch(url, options);
    const data = await res.json();

    const labels = ['Win', 'Draw', 'Lose'];
    const probs = data.probabilities;
    const labeledProbs = labels.map((label, i) => `${label} : ${(probs[i] * 100).toFixed(1)}%`).join('  /  ');
    const resultLabel = labels[[2, 1, 0].indexOf(data.result)];

    const team1 = selected[0];
    const team2 = selected[1];

    result.innerHTML = `
        ${team1} vs ${team2} → <br>
        Prediction: <strong>${team1} will ${resultLabel}!</strong><br>
        Probabilities: ${labeledProbs}
      `;
});
