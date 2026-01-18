// js/app.js
const tg = window.Telegram.WebApp;
tg.expand();  // Expand to full screen

const initData = tg.initData;  // Get initData
const headers = { 'Authorization': initData };

let chart;
let balance = 1000;

// Initialize chart
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
    const res = await fetch('/api/balance', { headers });
    const data = await res.json();
    balance = data.balance;
    document.getElementById('balance').innerText = `Balance: $${balance}`;
}

// Update chart and price
async function updatePrice() {
    const res = await fetch('/api/price', { headers });
    const data = await res.json();
    chart.data.labels = data.history.map((_, i) => i);
    chart.data.datasets[0].data = data.history;
    chart.update();
}

// Update open trades
async function updateOpenTrades() {
    const res = await fetch('/api/open-trades', { headers });
    const data = await res.json();
    document.getElementById('upTrades').innerHTML =
