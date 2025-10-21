// --- GLOBAL STATE & CONSTANTS ---
let sensors = [];
const sensorColors = ['#0e7fdbff', '#f5f22fff', '#38a164ff', '#ee1212ff', '#e2dedeff']; // Tailwind colors: blue, yellow, green, red, black

let currentView = 'live';
let historicalData = null;
let chartInstances = {}; // To store Chart.js instances
let socket;
let sessionData = { 1: [], 2: [], 3: [], 4: [], 5: [] };
let modalChartInstance = null;

// --- DOM ELEMENTS ---
const liveBtn = document.getElementById('live-btn');
const historyBtn = document.getElementById('history-btn');
const liveView = document.getElementById('live-view');
const historyView = document.getElementById('history-view');
const sensorCardsContainer = document.getElementById('sensor-cards');
const updateTimeDisplay = document.getElementById('update-time');
const sensorModal = document.getElementById('sensor-modal');
const modalContent = document.getElementById('modal-content');
const modalCloseBtn = document.getElementById('modal-close-btn');
const modalChartContainer = document.getElementById('modal-chart-container');

// --- UTILITY FUNCTIONS ---

/**
 * Generates mock historical data for 5 sensors
 */
const generateHistoricalData = (count = 20) => {
    const data = [];
    const baseTemp = 25;
    const baseHum = 50;
    const baseLight = 400;

    for (let i = 0; i < count; i++) {
        const time = new Date(Date.now() - (count - i) * 3600000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        data.push({
            time: time,
            // Temperature
            temp1: baseTemp + (Math.sin(i * 0.5) * 2) + Math.random() * 1.5,
            temp2: baseTemp + 1 + (Math.sin(i * 0.4) * 2.5) + Math.random() * 1.5,
            temp3: baseTemp - 2 + (Math.sin(i * 0.6) * 3) + Math.random() * 1.5,
            temp4: baseTemp + 3 + (Math.sin(i * 0.7) * 1.8) + Math.random() * 1.5,
            temp5: baseTemp - 1 + (Math.sin(i * 0.3) * 2.2) + Math.random() * 1.5,
            // Humidity
            hum1: baseHum + (Math.sin(i * 0.5) * 5) + Math.random() * 3,
            hum2: baseHum + 3 + (Math.sin(i * 0.4) * 6) + Math.random() * 3,
            hum3: baseHum - 4 + (Math.sin(i * 0.6) * 7) + Math.random() * 3,
            hum4: baseHum + 5 + (Math.sin(i * 0.7) * 4) + Math.random() * 3,
            hum5: baseHum - 2 + (Math.sin(i * 0.3) * 5) + Math.random() * 3,
            // Lightness
            light1: baseLight + (Math.sin(i * 0.5) * 50) + Math.random() * 20,
            light2: baseLight + 50 + (Math.sin(i * 0.4) * 60) + Math.random() * 20,
            light3: baseLight - 40 + (Math.sin(i * 0.6) * 70) + Math.random() * 20,
            light4: baseLight + 80 + (Math.sin(i * 0.7) * 40) + Math.random() * 20,
            light5: baseLight - 10 + (Math.sin(i * 0.3) * 50) + Math.random() * 20,
        });
    }
    return data;
};

// --- LIVE DATA HANDLING (WEBSOCKET) ---

const startLiveUpdates = () => {
    socket = new WebSocket(`wss://${window.location.host}/websocket`);

    socket.onmessage = function(event) {
        const newSensors = JSON.parse(event.data);
        sensors = newSensors;
        const time = new Date();

        newSensors.forEach(sensor => {
            if (sensor.status === 'Online') {
                sessionData[sensor.id].push({ ...sensor.data, time });
                if (sessionData[sensor.id].length > 100) { // Limit data points
                    sessionData[sensor.id].shift();
                }
            }
        });

        renderLiveView();
        if (!sensorModal.classList.contains('hidden')) {
            const sensorId = modalContent.dataset.sensorId;
            updateModalChart(sensorId);
        }
    };
};

const stopLiveUpdates = () => {
    if (socket) {
        socket.close();
    }
};

// --- UI RENDERING FUNCTIONS ---

/**
 * Renders a single sensor card HTML
 */
const renderSensorCard = (sensor) => {
    const color = sensorColors[sensor.id - 1];
    const isOffline = sensor.status === 'Offline';
    const statusClass = isOffline ? 'bg-red-800 text-red-100' : 'bg-green-700 text-green-100';
    const cardClasses = isOffline ?
        'bg-gray-900 border-2 border-red-600/50 opacity-70' :
        'bg-gray-800 border-t-4 border-l-2 border-opacity-70';
    const borderColor = isOffline ? '#DC2626' : color;

    let content;
    if (isOffline) {
        content = `
            <div class="text-center py-10">
                <p class="text-red-500 text-lg font-medium mb-4">
                    Sensor Offline / No Data Received
                </p>
                <button onclick="handleResetSensor(${sensor.id})" class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition duration-150 shadow-md">
                    Attempt Reset
                </button>
            </div>
        `;
    } else {
        content = `
            <div class="grid grid-cols-3 2xl:grid-cols-2 gap-4 place-content-center">
                <div class="flex flex-col items-center">
                    <p class="text-gray-400 text-sm mb-1">Temp</p>
                    <div class="text-3xl font-bold transition-all duration-500" style="color: ${color}">
                        ${sensor.data.temperature.toFixed(1)}°C
                    </div>
                </div>
                <div class="flex flex-col items-center">
                    <p class="text-gray-400 text-sm mb-1">Humidity</p>
                    <div class="text-3xl font-bold transition-all duration-500" style="color: ${color}">
                        ${sensor.data.humidity.toFixed(0)}%
                    </div>
                </div>
                <div class="flex flex-col items-center 2xl:col-span-2">
                    <p class="text-gray-400 text-sm mb-1">Lightness</p>
                    <div class="text-3xl font-bold transition-all duration-500" style="color: ${color}">
                        ${sensor.data.lightness.toFixed(0)} lux
                    </div>
                </div>
            </div>
        `;
    }

    return `
        <div 
            class="relative p-6 rounded-xl shadow-2xl transition-all duration-300 transform hover:scale-[1.02] ${cardClasses}"
            style="border-color: ${borderColor};" data-sensor-id="${sensor.id}"
        >
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-xl font-semibold ${isOffline ? 'text-red-400' : 'text-white'}">${sensor.name}</h3>
                <span class="px-3 py-1 text-xs font-medium rounded-full ${statusClass}">
                    ${sensor.status}
                </span>
            </div>
            ${content}
        </div>
    `;
};

/**
 * Renders the Live Data view content.
 */
const renderLiveView = () => {
    updateTimeDisplay.textContent = `Last Update: ${new Date().toLocaleTimeString()}`;
    sensorCardsContainer.innerHTML = sensors.map(renderSensorCard).join('');
};

// --- CHARTING FUNCTIONS (Chart.js) ---

/**
 * Destroys existing chart instances to prevent memory leaks and ghosting.
 */
const destroyCharts = () => {
    Object.values(chartInstances).forEach(chart => chart.destroy());
    chartInstances = {};
};

/**
 * Creates a Chart.js line chart.
 */
const createChart = (canvasId, title, dataKeys, unit) => {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const datasets = dataKeys.map((key, index) => ({
        label: `${sensors[index]?.name || `Sensor ${index + 1}`} ${unit}`,
        data: historicalData.map(d => d[key].toFixed(2)),
        borderColor: sensorColors[index],
        backgroundColor: sensorColors[index] + '40', // Semi-transparent fill
        tension: 0.4,
        pointRadius: 3,
        yAxisID: 'y',
    }));

    // Destroy previous instance if it exists
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }

    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: historicalData.map(d => d.time),
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#9CA3AF' } },
                tooltip: { backgroundColor: '#1F2937', bodyColor: '#E5E7EB', titleColor: '#E5E7EB' }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Time', color: '#9CA3AF' },
                    ticks: { color: '#9CA3AF' },
                    grid: { color: '#374151' }
                },
                y: {
                    title: { display: true, text: unit, color: '#9CA3AF' },
                    ticks: { color: '#9CA3AF', callback: (value) => `${value}${unit}` },
                    grid: { color: '#374151' }
                }
            }
        }
    });
};

/**
 * Renders the Historical Trends view content.
 */
const renderHistoryView = () => {
    if (!historicalData) {
        // Display loading or mock fetching message
        historyView.innerHTML = `
            <div class="flex items-center justify-center min-h-[50vh] p-8 text-xl text-blue-400 border-2 border-dashed border-blue-700 rounded-xl bg-gray-800/50">
                Loading Historical Data...
            </div>
        `;
        return;
    }

    if (historicalData.length === 0) {
        // Edge Case: No Historical Data
        destroyCharts(); // Ensure no blank charts are showing
        historyView.innerHTML = `
            <div class="flex items-center justify-center min-h-[50vh] p-8 text-xl text-yellow-400 border-2 border-dashed border-yellow-700 rounded-xl bg-gray-800/50">
                No Historical Records Found for this Period.
            </div>
        `;
        return;
    }

    // Charts are already in index.html, just create the Chart.js instances

    createChart('tempChart', 'Temperature', ['temp1', 'temp2', 'temp3', 'temp4', 'temp5'], '°C');
    createChart('humChart', 'Humidity', ['hum1', 'hum2', 'hum3', 'hum4', 'hum5'], '%');
    createChart('lightChart', 'Lightness', ['light1', 'light2', 'light3', 'light4', 'light5'], 'lux');
};

// --- MODAL LOGIC ---

const openModal = (sensorId) => {
    const sensor = sensors.find(s => s.id == sensorId);
    if (!sensor || sensor.status === 'Offline') return;

    modalContent.dataset.sensorId = sensorId;
    sensorModal.classList.remove('hidden');

    if (sessionData[sensorId].length === 0) {
        modalChartContainer.innerHTML = '<div class="no-data-message">No data has been received for this sensor yet.</div>';
    } else {
        createModalChart(sensorId);
    }
};

const closeModal = () => {
    sensorModal.classList.add('closing');
    setTimeout(() => {
        sensorModal.classList.add('hidden');
        sensorModal.classList.remove('closing');
        if (modalChartInstance) {
            modalChartInstance.destroy();
            modalChartInstance = null;
        }
        modalChartContainer.innerHTML = '<canvas id="modal-chart"></canvas>'; // Restore canvas
    }, 300);
};

const createModalChart = (sensorId) => {
    const sensor = sensors.find(s => s.id == sensorId);
    const data = sessionData[sensorId];
    const color = sensorColors[sensorId - 1];

    modalChartContainer.innerHTML = '<canvas id="modal-chart"></canvas>'; // Ensure canvas is present
    const ctx = document.getElementById('modal-chart').getContext('2d');

    if (modalChartInstance) {
        modalChartInstance.destroy();
    }

    modalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.time.toLocaleTimeString()),
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: data.map(d => d.temperature),
                    borderColor: '#ef4444',
                    yAxisID: 'y',
                },
                {
                    label: 'Humidity (%)',
                    data: data.map(d => d.humidity),
                    borderColor: '#3b82f6',
                    yAxisID: 'y1',
                },
                {
                    label: 'Lightness (lux)',
                    data: data.map(d => d.lightness),
                    borderColor: '#f59e0b',
                    yAxisID: 'y2',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: { display: true, text: `${sensor.name} - Live Data`, color: '#fff', font: { size: 18 } },
                legend: { labels: { color: '#9CA3AF' } },
            },
            scales: {
                x: { ticks: { color: '#9CA3AF' }, grid: { color: '#374151' } },
                y: { type: 'linear', display: true, position: 'left', title: { display: true, text: 'Temp (°C)', color: '#ef4444' }, ticks: { color: '#ef4444' } },
                y1: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'Humidity (%)', color: '#3b82f6' }, ticks: { color: '#3b82f6' }, grid: { drawOnChartArea: false } },
                y2: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'Lightness (lux)', color: '#f59e0b' }, ticks: { color: '#f59e0b' }, grid: { drawOnChartArea: false } }
            }
        }
    });
};

const updateModalChart = (sensorId) => {
    if (sessionData[sensorId].length > 0 && !modalChartInstance) {
        createModalChart(sensorId);
    }

    if (!modalChartInstance) return;

    const data = sessionData[sensorId];
    modalChartInstance.data.labels = data.map(d => d.time.toLocaleTimeString());
    modalChartInstance.data.datasets[0].data = data.map(d => d.temperature);
    modalChartInstance.data.datasets[1].data = data.map(d => d.humidity);
    modalChartInstance.data.datasets[2].data = data.map(d => d.lightness);
    modalChartInstance.update();
};

// --- APPLICATION LOGIC ---

/**
 * Switches the active view.
 */
const switchView = (view) => {
    if (currentView === view) return;

    currentView = view;

    liveBtn.className = (view === 'live')
        ? 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-blue-600 text-white shadow-blue-500/50'
        : 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-gray-700 text-gray-300 hover:bg-blue-500 hover:text-white';

    historyBtn.className = (view === 'history')
        ? 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-blue-600 text-white shadow-blue-500/50'
        : 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-gray-700 text-gray-300 hover:bg-blue-500 hover:text-white';

    if (view === 'live') {
        historyView.classList.add('slide-out-right');
        liveView.classList.remove('hidden', 'slide-out-left');
        liveView.classList.add('slide-in-left');
        setTimeout(() => {
            historyView.classList.add('hidden');
            historyView.classList.remove('slide-out-right');
            liveView.classList.remove('slide-in-left');
        }, 500);
        destroyCharts();
        startLiveUpdates();
    } else {
        liveView.classList.add('slide-out-left');
        historyView.classList.remove('hidden', 'slide-out-right');
        historyView.classList.add('slide-in-right');
        setTimeout(() => {
            liveView.classList.add('hidden');
            liveView.classList.remove('slide-out-left');
            historyView.classList.remove('slide-in-right');
        }, 500);
        stopLiveUpdates();

        if (!historicalData) {
            fetchHistoricalData();
        } else {
            renderHistoryView();
        }
    }
};

/**
 * Mock API call to fetch historical data.
 */
const fetchHistoricalData = async () => {
    await new Promise(resolve => setTimeout(resolve, 500));
    historicalData = generateHistoricalData();
    renderHistoryView();
};

/**
 * Handler for resetting a failed sensor (linked via inline onclick).
 */
window.handleResetSensor = (id) => {
    // This is now handled by the server, but we can keep a client-side optimistic update
    const sensor = sensors.find(s => s.id === id);
    if (sensor) {
        sensor.status = 'Online';
        sensor.data = { temperature: 22, humidity: 55, lightness: 350 }; // Placeholder
        renderLiveView();
    }
};

// --- INITIALIZATION ---
window.onload = function () {
    liveBtn.addEventListener('click', () => switchView('live'));
    historyBtn.addEventListener('click', () => switchView('history'));
    modalCloseBtn.addEventListener('click', closeModal);
    sensorCardsContainer.addEventListener('click', (e) => {
        const card = e.target.closest('[data-sensor-id]');
        if (card) {
            openModal(card.dataset.sensorId);
        }
    });
    sensorModal.addEventListener('click', (e) => {
        if (e.target === sensorModal) {
            closeModal();
        }
    });

    renderLiveView();
    startLiveUpdates();
};