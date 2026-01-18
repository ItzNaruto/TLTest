// js/app.js
const tg = window.Telegram.WebApp;
tg.expand();

const initData = tg.initData;
const apiBase = 'https://tl-test.vercel.app';  // Replace with your actual Vercel URL (e.g., 'https://tltest.vercel.app')
const headers = { 'Authorization': initData };

let chart;
let balance = 1000;

// Initialize chart (unchanged)
function initChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [{ data: [], borderColor: '#00ff00', fill: false }] },
        options: { animation: { duration: 0 }, scales: { x: { display: false } } }
    });
}

// Update balance
async function updateBalance() {
    try {
        const res = await fetch(`${apiBase}/api/balance`, { headers });
        if (!res.ok) throw new Error(`Balance API failed: ${res.status}`);
        const data = await res.json();
        balance = data.balance;
        document.getElementById('balance').innerText = `Balance: $${balance}`;
    } catch (error) {
        console.error('Balance update error:', error);
        // Fallback: Show error in UI
        document.getElementById('balance').innerText = 'Balance: Error loading';
    }
}

// Update chart and price
async function updatePrice() {
    try {
        const res = await fetch(`${apiBase}/api/price`, { headers });
        if (!res.ok) throw new Error(`Price API failed: ${res.status}`);
        const data = await res.json();
        chart.data.labels = data.history.map((_, i) => i);
        chart.data.datasets[0].data = data.history;
        chart.update();
    } catch (error) {
        console.error('Price update error:', error);
    }
}

// Update open trades
async function updateOpenTrades() {
    try {
        const res = await fetch(`${apiBase}/api/open-trades`, { headers });
        if (!res.ok) throw new Error(`Open trades API failed: ${res.status}`);
        const data = await res.json();
        document.getElementById('upTrades').innerHTML = data.up.map(t => `<li>${t.username}: $${t.amount}</li>`).join('');
        document.getElementById('downTrades').innerHTML = data.down.map(t => `<li>${t.username}: $${t.amount}</li>`).join('');
    } catch (error) {
        console.error('Open trades update error:', error);
    }
}

// Update history
async function updateHistory() {
    try {
        const res = await fetch(`${apiBase}/api/history`, { headers });
        if (!res.ok) throw new Error(`History API failed: ${res.status}`);
        const data = await res.json();
        document.getElementById('historyList').innerHTML = data.map(t => `<li>${t.username}: $${t.amount} (${t.direction}) - ${t.result} (${t.profit_amount})</li>`).join('');
    } catch (error) {
        console.error('History update error:', error);
    }
}

// Place trade
document.getElementById('betUp').addEventListener('click', async () => {
    const amount = parseFloat(document.getElementById('betAmount').value);
    if (isNaN(amount) || amount <= 0) return alert('Invalid amount');
    try {
        const res = await fetch(`${apiBase}/api/trade`, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, direction: 'UP' })
        });
        if (!res.ok) throw new Error(`Trade API failed: ${res.status}`);
        alert('Trade placed!');
        updateBalance();  // Refresh after trade
    } catch (error) {
        console.error('Trade error:', error);
        alert('Trade failed: ' + error.message);
    }
});

// Same for betDown (copy and change 'UP' to 'DOWN')

// Polling for real-time updates
setInterval(() => {
    updatePrice();
    updateOpenTrades();
    updateHistory();
}, 2000);

// Init on load
window.onload = () => {
    initChart();
    updateBalance();
    updatePrice();
    updateOpenTrades();
    updateHistory();
};
