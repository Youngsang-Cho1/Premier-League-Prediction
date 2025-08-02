const teamColors = {
    // red color teams
    "Arsenal": "rgba(239, 1, 7, 0.8)",           
    "Liverpool": "rgba(200, 16, 46, 0.8)",           
    "Manchester Utd": "rgba(218, 41, 28, 0.8)",  
    "Southampton": "rgba(215, 25, 32, 0.8)",         
    "Nott'ham Forest": "rgba(221, 38, 38, 0.8)",      
    "Burnley": "rgba(108, 29, 69, 0.8)",             
    "Sheffield Utd": "rgba(238, 54, 36, 0.8)",      

    // blue color teams
    "Chelsea": "rgba(3, 70, 148, 0.8)",              
    "Manchester City": "rgba(108, 171, 221, 0.8)",   
    "Everton": "rgba(39, 68, 136, 0.8)",             
    "Leicester City": "rgba(67, 126, 191, 0.8)",     
    "Brighton": "rgba(0, 87, 184, 0.8)", 
    "Tottenham": "rgba(19, 31, 83, 0.8)",             

    // purple & magenta color teams
    "Aston Villa": "rgba(149, 191, 229, 0.8)",         
    "West Ham": "rgba(122, 38, 82, 0.8)",            
    "Crystal Palace": "rgba(27, 69, 143, 0.8)",      

    // white color teams
    "Leeds United": "rgba(255, 255, 255, 0.8)",      
    "Newcastle Utd": "rgba(45, 45, 45, 0.8)",        
    "Fulham": "rgba(0, 0, 0, 0.8)",                  

    // yellow color teams
    "Norwich City": "rgba(255, 193, 7, 0.8)",        
    "Watford": "rgba(251, 197, 49, 0.8)",            
    "Wolves": "rgba(253, 185, 19, 0.8)",             

    // orange/red combined color teams
    "Luton Town": "rgba(255, 140, 0, 0.8)",          
    "Bournemouth": "rgba(218, 41, 28, 0.8)",        
    "Brentford": "rgba(214, 41, 54, 0.8)"           
};


const premTeams = (['Manchester City', 'Arsenal', 'Liverpool',
    'Tottenham', 'Chelsea', 'Manchester Utd', 'Newcastle Utd', 'Aston Villa', 'West Ham',
    'Crystal Palace', 'Wolves', 'Brighton', 'Bournemouth', 'Leicester City', 'Fulham', 'Everton', 'Brentford',
    "Nott'ham Forest", 'Luton Town', 'Burnley', 'Sheffield Utd', 'Leeds United',
    'Southampton', 'Watford', 'Norwich City'])

let selected = []


document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('teamGrid');
    const predictBtn = document.getElementById('predictBtn');
    const loading =  document.getElementById('loading');
    const team1Image = document.getElementById('team1Image');
    const team2Image = document.getElementById('team2Image');
    const resultContainer = document.getElementById('resultContainer');
    const vsText = document.getElementById('vsText');
    const result = document.getElementById('result');
    const resetBtn = document.getElementById('resetBtn');

    function normalizeTeamName(name) {
        return name.replace(" ", "-").replace("'", "");
    }

    function showResults() {
        grid.classList.add('hidden')
        predictBtn.classList.add('hidden')
        resultContainer.classList.remove('hidden')
        vsText.classList.remove('hidden')
        team1Image.classList.remove('hidden')
        team2Image.classList.remove('hidden')
        result.classList.remove('hidden')
        resetBtn.classList.remove('hidden')
    }

    function hideResults() {
        grid.classList.remove('hidden')
        predictBtn.classList.remove('hidden')
        resultContainer.classList.add('hidden')
        vsText.classList.add('hidden')
        team1Image.classList.add('hidden')
        team2Image.classList.add('hidden')
        result.classList.add('hidden')
        resetBtn.classList.add('hidden')
    }

    premTeams.forEach(team => {
        const div = document.createElement('div');
        div.classList.add('team')

        const color = teamColors[team] || 'rgba(255,255,255,0.25)';
        div.style.backgroundColor = color;

        const teamName = normalizeTeamName(team)
        div.style.backgroundImage = `url(/static/images/${teamName}-logo.png)`;

        const name = document.createElement('span');
        name.classList.add('team-name');
        name.textContent = team;
        div.appendChild(name);

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
        grid.classList.add('hidden');
        predictBtn.classList.add('hidden');
        loading.classList.remove('hidden');

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

        await new Promise(resolve => setTimeout(resolve, 3000));

        loading.classList.add('hidden');

        const team1 = selected[0];
        const team2 = selected[1];
        const team1Name = normalizeTeamName(team1);
        const team2Name = normalizeTeamName(team2);

        team1Image.src = `/static/images/${team1Name}-logo.png`;
        team2Image.src = `/static/images/${team2Name}-logo.png`;

        if (data.result === -1) {
            result.innerHTML = `
                ${team1} vs ${team2} → <br>
                Prediction Unavailable: <strong> No Premier League match history found between ${team1} and ${team2}.</strong><br>
            `;
            showResults();
            return;
        }

        const labels = ['Win', 'Draw', 'Lose'];
        const probs = data.probabilities;
        const labeledProbs = labels.map((label, i) => `${label} : ${(probs[i] * 100).toFixed(1)}%`).join('  /  ');
        const resultLabel = labels[[2, 1, 0].indexOf(data.result)];

        const win_prob = probs[2];
        const draw_prob = probs[1];
        const lose_prob = probs[0];

        if (Math.abs(win_prob - lose_prob) < 0.07 && draw_prob > 0.25) {
            result.innerHTML = `
                ${team1} vs ${team2} → <br>
                Prediction: Close match. Still, <strong class = "${resultLabel.toLowerCase()}">${team1} is slightly more likely to ${resultLabel}.</strong><br>
                Probabilities: ${labeledProbs}
            `;
        }
        else {
            result.innerHTML = `
                ${team1} vs ${team2} → <br>
                Prediction: <strong  class = "${resultLabel.toLowerCase()}">${team1} expected to ${resultLabel}.</strong><br>
                Probabilities: ${labeledProbs}
            `;
        }
        showResults();
    });

    resetBtn.addEventListener('click', () => {
        selected = [];
        document.querySelectorAll('.team.selected').forEach(el => el.classList.remove('selected'));
        hideResults();
    });
});
