// --- GLOBAL STATE & CONSTANTS ---
let sensors = [
    { id: 1, name: 'Main Server Rack', data: { temperature: 25.5, humidity: 45, lightness: 300 }, status: 'Online' },
    { id: 2, name: 'West Wing HVAC', data: { temperature: 23.1, humidity: 55, lightness: 450 }, status: 'Online' },
    { id: 3, name: 'Warehouse Entry', data: null, status: 'Offline' },
    { id: 4, name: 'Data Center Core', data: { temperature: 28.9, humidity: 40, lightness: 600 }, status: 'Online' },
    { id: 5, name: 'Roof Access', data: null, status: 'Offline' },
];
const sensorColors = ['#4299E1', '#F6AD55', '#48BB78', '#ED64A6', '#ECC94B']; // Tailwind colors: blue, orange, green, pink, yellow

let currentView = 'live';
let historicalData = null;
let chartInstances = {}; // To store Chart.js instances

// --- DOM ELEMENTS ---
const liveBtn = document.getElementById('live-btn');
const historyBtn = document.getElementById('history-btn');
const liveView = document.getElementById('live-view');
const historyView = document.getElementById('history-view');
const sensorCardsContainer = document.getElementById('sensor-cards');
const updateTimeDisplay = document.getElementById('update-time');

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

// --- LIVE DATA HANDLING (MOCK WEBSOCKET) ---

let liveDataInterval;

const updateLiveData = () => {
    sensors = sensors.map(sensor => {
        if (sensor.status === 'Online' && sensor.data) {
            return {
                ...sensor,
                data: {
                    temperature: sensor.data.temperature + (Math.random() * 0.5 - 0.25),
                    humidity: sensor.data.humidity + (Math.random() * 1.0 - 0.5),
                    lightness: sensor.data.lightness + (Math.random() * 10 - 5),
                }
            };
        }
        return sensor;
    });
    renderLiveView();
};

const startLiveUpdates = () => {
    if (liveDataInterval) clearInterval(liveDataInterval);
    liveDataInterval = setInterval(updateLiveData, 2000); // 2-second update
};

const stopLiveUpdates = () => {
    if (liveDataInterval) clearInterval(liveDataInterval);
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
                    <div class="grid grid-cols-3 gap-4">
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
                        <div class="flex flex-col items-center">
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
                    style="border-color: ${borderColor};"
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
        label: `Sensor ${index + 1} ${unit}`,
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

    // Restore chart containers before rendering charts
    historyView.innerHTML = `
                <div id="temp-chart-container" class="bg-gray-800 p-6 rounded-2xl shadow-xl transition duration-300 hover:shadow-2xl hover:bg-gray-700/80">
                    <h3 class="text-xl font-semibold mb-4 text-white border-b border-gray-600 pb-2">Temperature Trends (°C)</h3>
                    <div class="chart-container"><canvas id="tempChart"></canvas></div>
                </div>
                <div id="hum-chart-container" class="bg-gray-800 p-6 rounded-2xl shadow-xl transition duration-300 hover:shadow-2xl hover:bg-gray-700/80">
                    <h3 class="text-xl font-semibold mb-4 text-white border-b border-gray-600 pb-2">Humidity Trends (%)</h3>
                    <div class="chart-container"><canvas id="humChart"></canvas></div>
                </div>
                <div id="light-chart-container" class="bg-gray-800 p-6 rounded-2xl shadow-xl transition duration-300 hover:shadow-2xl hover:bg-gray-700/80">
                    <h3 class="text-xl font-semibold mb-4 text-white border-b border-gray-600 pb-2">Lightness Trends (lux)</h3>
                    <div class="chart-container"><canvas id="lightChart"></canvas></div>
                </div>
            `;

    createChart('tempChart', 'Temperature', ['temp1', 'temp2', 'temp3', 'temp4', 'temp5'], '°C');
    createChart('humChart', 'Humidity', ['hum1', 'hum2', 'hum3', 'hum4', 'hum5'], '%');
    createChart('lightChart', 'Lightness', ['light1', 'light2', 'light3', 'light4', 'light5'], 'lux');
};

// --- APPLICATION LOGIC ---

/**
 * Switches the active view.
 */
const switchView = (view) => {
    currentView = view;

    // Update button styles
    liveBtn.className = (view === 'live')
        ? 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-blue-600 text-white shadow-blue-500/50'
        : 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-gray-700 text-gray-300 hover:bg-blue-500 hover:text-white';

    historyBtn.className = (view === 'history')
        ? 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-blue-600 text-white shadow-blue-500/50'
        : 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-gray-700 text-gray-300 hover:bg-blue-500 hover:text-white';

    // Show/Hide views
    if (view === 'live') {
        liveView.classList.remove('hidden');
        historyView.classList.add('hidden');
        destroyCharts(); // Ensure charts are removed when leaving history
        startLiveUpdates();
    } else {
        liveView.classList.add('hidden');
        historyView.classList.remove('hidden');
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
    // Simulate network latency
    await new Promise(resolve => setTimeout(resolve, 500));

    historicalData = generateHistoricalData();
    // To test the "No Data" edge case, uncomment the line below:
    // historicalData = []; 

    renderHistoryView();
};

/**
 * Handler for resetting a failed sensor (linked via inline onclick).
 */
window.handleResetSensor = (id) => {
    sensors = sensors.map(sensor => {
        if (sensor.id === id) {
            // Reset to a new, random online state
            return {
                ...sensor,
                data: {
                    temperature: (20 + Math.random() * 10),
                    humidity: (40 + Math.random() * 20),
                    lightness: (200 + Math.random() * 400),
                },
                status: 'Online',
            };
        }
        return sensor;
    });
    renderLiveView(); // Re-render the live view after reset
};

// --- INITIALIZATION ---
window.onload = function () {
    // Event Listeners
    liveBtn.addEventListener('click', () => switchView('live'));
    historyBtn.addEventListener('click', () => switchView('history'));

    // Initial render and start updates
    renderLiveView();
    startLiveUpdates();
};