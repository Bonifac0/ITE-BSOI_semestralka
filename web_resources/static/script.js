// --- GLOBAL STATE & CONSTANTS ---
let sensors = [
    { id: 1, name: 'Blue Team', data: null, lastUpdate: null, status: 'Offline' },
    { id: 2, name: 'Yellow Team', data: null, lastUpdate: null, status: 'Offline' },
    { id: 3, name: 'Green Team', data: null, lastUpdate: null, status: 'Offline' },
    { id: 4, name: 'Red Team', data: null, lastUpdate: null, status: 'Offline' },
    { id: 5, name: 'Black Team', data: null, lastUpdate: null, status: 'Offline' },
];
const sensorColors = ['#0e7fdbff', '#f5f22fff', '#38a164ff', '#ee1212ff', '#e2dedeff']; // Tailwind colors: blue, yellow, green, red, black

let currentView = 'live';
let historicalData = null;
let chartInstances = {}; // To store Chart.js instances
let socket;
let sessionData = { 1: [], 2: [], 3: [], 4: [], 5: [] };
let modalChartInstance = null;
let currentRange = '1h';

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
const timeRangeSelector = document.getElementById('time-range-selector');

// --- LIVE DATA HANDLING (WEBSOCKET) ---

const startLiveUpdates = () => {
    socket = new WebSocket(`wss://aether70.zcu.cz/websocket`);

    socket.onmessage = function (event) {
        const message = JSON.parse(event.data);
        const teamToId = { 'blue': 1, 'yellow': 2, 'green': 3, 'red': 4, 'black': 5 };

        if (message.type === 'initial_data') {
            const initialRecords = message.payload;
            console.log('Processing initial_data:', initialRecords);

            // Group initial records by sensor ID, keeping only the latest for each.
            const latestRecords = {};
            initialRecords.forEach(record => {
                const id = teamToId[record.team.toLowerCase()];
                if (id) {
                    // Since records are sorted by time, the last one for each ID will be the latest.
                    latestRecords[id] = record;
                }
            });

            // Update the main sensors array with the latest initial data
            sensors = sensors.map(sensor => {
                const latestRecord = latestRecords[sensor.id];
                if (latestRecord) {
                    const recordTime = new Date(latestRecord.time);
                    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
                    return {
                        ...sensor,
                        data: {
                            temperature: latestRecord.temperature,
                            humidity: latestRecord.humidity,
                            lightness: latestRecord.lightness,
                        },
                        lastUpdate: recordTime,
                        status: recordTime > fiveMinutesAgo ? 'Online' : 'Offline',
                    };
                }
                return sensor; // Return sensor unchanged if no initial data
            });

            // Populate sessionData for modal charts with a consistent structure
            initialRecords.forEach(record => {
                const id = teamToId[record.team.toLowerCase()];
                if (id) {
                    sessionData[id].push({
                        temperature: record.temperature,
                        humidity: record.humidity,
                        lightness: record.lightness,
                        time: new Date(record.time)
                    });
                }
            });

        } else if (message.type === 'update') {
            const updatedRecord = message.payload;
            const recordTime = new Date(updatedRecord.time);

            // Update the sensor in the main array
            sensors = sensors.map(sensor => {
                if (sensor.id === updatedRecord.id) {
                    return {
                        ...sensor,
                        data: updatedRecord.data,
                        lastUpdate: recordTime,
                        status: 'Online' // Immediately mark as online
                    };
                }
                return sensor;
            });

            // Add to session data for modal graph
            sessionData[updatedRecord.id].push({ ...updatedRecord.data, time: recordTime });
        }

        console.log('Calling renderLiveView from onmessage');
        renderLiveView();

        if (!sensorModal.classList.contains('hidden')) {
            const sensorId = parseInt(modalContent.dataset.sensorId, 10);
            if (message.type === 'update' && message.payload.id === sensorId) {
                updateModalChart(sensorId);
            }
        }
    };
};

const stopLiveUpdates = () => {
    if (socket) {
        socket.close();
    }
};

// --- SENSOR STATUS CHECK ---

const checkSensorStatus = () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    let needsRender = false;

    sensors.forEach(sensor => {
        const newStatus = (sensor.lastUpdate && sensor.lastUpdate > fiveMinutesAgo) ? 'Online' : 'Offline';
        if (sensor.status !== newStatus) {
            sensor.status = newStatus;
            needsRender = true;
        }
    });

    if (needsRender) {
        renderLiveView();
    }
};

// --- UI RENDERING FUNCTIONS ---

const renderSensorCard = (sensor) => {
    const color = sensorColors[sensor.id - 1];
    const isOffline = sensor.status === 'Offline';
    const statusClass = isOffline ? 'bg-red-800 text-red-100' : 'bg-green-700 text-green-100';
    const cardClasses = isOffline ? 'bg-gray-900 border-2 border-red-600/50 opacity-70' : 'bg-gray-800 border-t-4 border-l-2 border-opacity-70';
    const borderColor = isOffline ? '#DC2626' : color;

    let content;
    if (isOffline || !sensor.data) {
        content = `<div class="text-center py-4"><p class="text-red-500 text-lg font-medium mb-4">Sensor Offline</p></div>`;
    } else {
        const temp = sensor.data.temperature;
        const hum = sensor.data.humidity;
        const light = sensor.data.lightness;
        content = `
            <div class="grid grid-cols-3 2xl:grid-cols-2 gap-4 place-content-center">
                <div class="flex flex-col items-center">
                    <p class="text-gray-400 text-sm mb-1">Temp</p>
                    <div class="text-3xl font-bold" style="color: ${color}">${temp.toFixed(1)}°C</div>
                </div>
                <div class="flex flex-col items-center">
                    <p class="text-gray-400 text-sm mb-1">Humidity</p>
                    <div class="text-3xl font-bold" style="color: ${color}">${hum !== null && hum !== undefined ? hum.toFixed(0) + '%' : '--'}</div>
                </div>
                <div class="flex flex-col items-center 2xl:col-span-2">
                    <p class="text-gray-400 text-sm mb-1">Lightness</p>
                    <div class="text-3xl font-bold" style="color: ${color}">${light !== null && light !== undefined ? light.toFixed(0) + ' lux' : '--'}</div>
                </div>
            </div>`;
    }

    return `
        <div class="relative p-6 rounded-xl shadow-2xl transition-all duration-300 transform hover:scale-[1.02] ${cardClasses}" style="border-color: ${borderColor};" data-sensor-id="${sensor.id}">
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-xl font-semibold ${isOffline ? 'text-red-400' : 'text-white'}">${sensor.name}</h3>
                <span class="px-3 py-1 text-xs font-medium rounded-full ${statusClass}">${sensor.status}</span>
            </div>
            ${content}
        </div>`;
};

const renderLiveView = () => {
    console.log('Rendering Live View. Sensors state:', JSON.parse(JSON.stringify(sensors)));
    updateTimeDisplay.textContent = `Last Update: ${new Date().toLocaleTimeString()}`;
    sensorCardsContainer.innerHTML = sensors.map(renderSensorCard).join('');
};

// --- CHARTING FUNCTIONS (Chart.js) ---

const destroyCharts = () => {
    Object.values(chartInstances).forEach(chart => chart.destroy());
    chartInstances = {};
};

const createChart = (canvasId, title, dataKeys, unit) => {
    const chartContainer = document.getElementById(canvasId).parentElement;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
        delete chartInstances[canvasId];
    }

    const datasets = dataKeys.map((key, index) => ({
        label: `${sensors[index]?.name || `Sensor ${index + 1}`} ${unit}`,
        data: historicalData.map(d => ({ x: d.time, y: d[key] !== null ? d[key].toFixed(2) : null })),
        borderColor: sensorColors[index],
        backgroundColor: sensorColors[index] + '40',
        tension: 0.4,
        pointRadius: 3,
        yAxisID: 'y',
        spanGaps: true, // Draw a line over null values
        segment: {
            borderDash: ctx => (ctx.p1DataIndex - ctx.p0DataIndex > 1) ? [6, 6] : undefined,
        }
    }));

    const hasData = datasets.some(ds => ds.data.some(point => point.y !== null));

    if (!hasData) {
        chartContainer.innerHTML = `<div class="flex items-center justify-center h-full min-h-[350px] text-xl text-yellow-400">No Records Found for this Period.</div>`;
        return;
    }

    let suggestedMin, suggestedMax;
    if (unit === '°C') {
        suggestedMin = 18;
        suggestedMax = 23;
    } else if (unit === '%') {
        suggestedMin = 30;
        suggestedMax = 70;
    } else if (unit === 'lux') {
        suggestedMin = 0;
        suggestedMax = 100;
    }

    const ctx = document.getElementById(canvasId).getContext('2d');
    chartInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { labels: { color: '#9CA3AF' } },
                tooltip: {
                    position: 'nearest',
                    backgroundColor: '#1F2937',
                    bodyColor: '#E5E7EB',
                    titleColor: '#E5E7EB'
                }
            },
            scales: {
                x: {
                    type: 'timeseries',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'yyyy-MM-dd HH:mm',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm'
                        }
                    },
                    title: { display: true, text: 'Time', color: '#9CA3AF' },
                    ticks: { color: '#9CA3AF' },
                    grid: { color: '#374151' }
                },
                y: {
                    suggestedMin: suggestedMin,
                    suggestedMax: suggestedMax,
                    title: { display: true, text: unit, color: '#9CA3AF' },
                    ticks: {
                        color: '#9CA3AF',
                        callback: (value) => {
                            if (unit === '°C') {
                                return `${value.toFixed(2)}${unit}`;
                            } else if (unit === '%') {
                                return `${value.toFixed(1)}${unit}`;
                            }
                            return `${value}${unit}`;
                        }
                    },
                    grid: { color: '#374151' }
                }
            }
        }
    });
};

const renderHistoryView = () => {
    const tempContainer = document.getElementById('temp-chart-container').querySelector('.chart-container');
    const humContainer = document.getElementById('hum-chart-container').querySelector('.chart-container');
    const lightContainer = document.getElementById('light-chart-container').querySelector('.chart-container');

    if (historicalData === null) {
        const loadingHTML = '<div class="flex items-center justify-center min-h-[350px] text-xl text-blue-400">Loading Historical Data...</div>';
        tempContainer.innerHTML = loadingHTML;
        humContainer.innerHTML = loadingHTML;
        lightContainer.innerHTML = loadingHTML;
        return;
    }

    tempContainer.innerHTML = '<canvas id="tempChart"></canvas>';
    humContainer.innerHTML = '<canvas id="humChart"></canvas>';
    lightContainer.innerHTML = '<canvas id="lightChart"></canvas>';

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
        modalChartContainer.innerHTML = '<canvas id="modal-chart"></canvas>';
    }, 300);
};

const createModalChart = (sensorId) => {
    const sensor = sensors.find(s => s.id == sensorId);
    const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
    const chartData = sessionData[sensorId].filter(d => d.time > tenMinutesAgo);

    modalChartContainer.innerHTML = '<canvas id="modal-chart"></canvas>';
    const ctx = document.getElementById('modal-chart').getContext('2d');

    if (modalChartInstance) modalChartInstance.destroy();

    modalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: chartData.map(d => ({ x: d.time, y: d.temperature })),
                    borderColor: '#ef4444',
                    yAxisID: 'y'
                },
                {
                    label: 'Humidity (%)',
                    data: chartData.map(d => ({ x: d.time, y: d.humidity })),
                    borderColor: '#3b82f6',
                    yAxisID: 'y1'
                },
                {
                    label: 'Lightness (lux)',
                    data: chartData.map(d => ({ x: d.time, y: d.lightness })),
                    borderColor: '#f59e0b',
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                title: {
                    display: true,
                    text: `${sensor.name} - Live Data (Last 10 Minutes)`,
                    color: '#fff',
                    font: { size: 18 }
                },
                legend: { labels: { color: '#9CA3AF' } },
                tooltip: {
                    position: 'nearest',
                }
            },
            scales: {
                x: {
                    type: 'timeseries',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'yyyy-MM-dd HH:mm',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm'
                        }
                    },
                    ticks: { color: '#9CA3AF' },
                    grid: { color: '#374151' }
                },
                y: { type: 'linear', display: true, position: 'left', title: { display: true, text: 'Temp (°C)', color: '#ef4444' }, ticks: { color: '#ef4444' } },
                y1: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'Humidity (%)', color: '#3b82f6' }, ticks: { color: '#3b82f6' }, grid: { drawOnChartArea: false } },
                y2: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'Lightness (lux)', color: '#f59e0b' }, ticks: { color: '#f59e0b' }, grid: { drawOnChartArea: false } }
            }
        }
    });
};

const updateModalChart = (sensorId) => {
    if (!modalChartInstance) {
        createModalChart(sensorId);
        return;
    }

    const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
    const chartData = sessionData[sensorId].filter(d => d.time > tenMinutesAgo);

    modalChartInstance.data.datasets[0].data = chartData.map(d => ({ x: d.time, y: d.temperature }));
    modalChartInstance.data.datasets[1].data = chartData.map(d => ({ x: d.time, y: d.humidity }));
    modalChartInstance.data.datasets[2].data = chartData.map(d => ({ x: d.time, y: d.lightness }));
    modalChartInstance.update('none'); // 'none' for no animation
};

// --- APPLICATION LOGIC ---

const updateActiveRangeButton = (newRange) => {
    currentRange = newRange;
    const buttons = timeRangeSelector.querySelectorAll('.time-range-btn');
    buttons.forEach(button => {
        if (button.dataset.range === newRange) {
            button.classList.add('bg-blue-600', 'text-white');
            button.classList.remove('bg-gray-700', 'text-gray-300', 'hover:bg-gray-600');
        } else {
            button.classList.remove('bg-blue-600', 'text-white');
            button.classList.add('bg-gray-700', 'text-gray-300', 'hover:bg-gray-600');
        }
    });
};

const switchView = (view) => {
    if (currentView === view || liveBtn.disabled) return;
    currentView = view;
    liveBtn.disabled = true;
    historyBtn.disabled = true;

    liveBtn.className = (view === 'live')
        ? 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-blue-600 text-white shadow-blue-500/50'
        : 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-gray-700 text-gray-300 hover:bg-blue-500 hover:text-white';

    historyBtn.className = (view === 'history')
        ? 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-blue-600 text-white shadow-blue-500/50'
        : 'px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg bg-gray-700 text-gray-300 hover:bg-blue-500 hover:text-white';

    const viewToShow = (view === 'live') ? liveView : historyView;
    const viewToHide = (view === 'live') ? historyView : liveView;
    const container = document.getElementById('view-container');

    viewToShow.style.visibility = 'hidden';
    viewToShow.classList.remove('hidden');
    const newHeight = viewToShow.scrollHeight;
    viewToShow.classList.add('hidden');
    viewToShow.style.visibility = '';

    container.style.minHeight = `${newHeight}px`;
    viewToHide.classList.add('view-exit');

    setTimeout(() => {
        viewToHide.classList.add('hidden');
        viewToHide.classList.remove('view-exit');
        viewToShow.classList.remove('hidden');
        viewToShow.classList.add('view-enter');

        if (view === 'live') {
            destroyCharts();
            startLiveUpdates();
        } else {
            stopLiveUpdates();
            fetchHistoricalData(currentRange);
        }

        setTimeout(() => {
            viewToShow.classList.remove('view-enter');
            liveBtn.disabled = false;
            historyBtn.disabled = false;
        }, 500);
    }, 300);
};

const fetchHistoricalData = async (range = '1h') => {
    historicalData = null;
    renderHistoryView();

    const teamToId = { 'blue': 1, 'yellow': 2, 'green': 3, 'red': 4, 'black': 5 };

    try {
        const response = await fetch(`https://aether70.zcu.cz/api/history?range=${range}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const rawData = await response.json();

        if (!rawData || rawData.length === 0) {
            historicalData = [];
        } else {
            const groupedData = {};
            rawData.forEach(d => {
                const date = new Date(d.time);
                const timeKey = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()} ${date.getHours()}:${date.getMinutes()}`;

                if (!groupedData[timeKey]) {
                    groupedData[timeKey] = { time: date }; // Store the Date object
                    for (let i = 1; i <= 5; i++) {
                        groupedData[timeKey]['temp' + i] = null;
                        groupedData[timeKey]['hum' + i] = null;
                        groupedData[timeKey]['light' + i] = null;
                    }
                }
                const id = teamToId[d.team.toLowerCase()];
                if (id) {
                    groupedData[timeKey]['temp' + id] = d.temperature;
                    groupedData[timeKey]['hum' + id] = d.humidity;
                    groupedData[timeKey]['light' + id] = d.lightness;
                }
            });
            historicalData = Object.values(groupedData).sort((a, b) => a.time - b.time);
        }
    } catch (error) {
        console.error("Could not fetch historical data:", error);
        historicalData = [];
    } finally {
        renderHistoryView();
    }
};

// --- INITIALIZATION ---
window.onload = function () {
    liveBtn.addEventListener('click', () => switchView('live'));
    if (historyBtn) {
        historyBtn.addEventListener('click', () => switchView('history'));
    }
    modalCloseBtn.addEventListener('click', closeModal);

    sensorCardsContainer.addEventListener('click', (e) => {
        const card = e.target.closest('[data-sensor-id]');
        if (card) openModal(card.dataset.sensorId);
    });

    sensorModal.addEventListener('click', (e) => {
        if (e.target === sensorModal) closeModal();
    });

    timeRangeSelector.addEventListener('click', (e) => {
        const button = e.target.closest('.time-range-btn');
        if (button) {
            const newRange = button.dataset.range;
            if (newRange !== currentRange) {
                updateActiveRangeButton(newRange);
                fetchHistoricalData(newRange);
            }
        }
    });

    renderLiveView();
    startLiveUpdates();
    setInterval(checkSensorStatus, 10000); // Check sensor status every 10 seconds
};