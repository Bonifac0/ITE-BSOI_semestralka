import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { BarChart, Bar } from 'recharts'; // Used for the Live View as a subtle indicator

// Mock initial state data
const initialSensors = [
    { id: 1, name: 'Main Server Rack', data: { temperature: 25.5, humidity: 45, lightness: 300 }, status: 'Online' },
    { id: 2, name: 'West Wing HVAC', data: { temperature: 23.1, humidity: 55, lightness: 450 }, status: 'Online' },
    { id: 3, name: 'Warehouse Entry', data: null, status: 'Offline' }, // Critical Edge Case 1: Initial Failure
    { id: 4, name: 'Data Center Core', data: { temperature: 28.9, humidity: 40, lightness: 600 }, status: 'Online' },
    { id: 5, name: 'Roof Access', data: null, status: 'Offline' }, // Critical Edge Case 2: Initial Failure
];

const sensorColors = ['#4299E1', '#F6AD55', '#48BB78', '#ED64A6', '#ECC94B'];

// Utility function to generate mock historical data
const generateHistoricalData = (count = 20) => {
    const data = [];
    const baseTemp = 25;
    const baseHum = 50;
    const baseLight = 400;

    for (let i = 0; i < count; i++) {
        const time = new Date(Date.now() - (count - i) * 3600000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        data.push({
            time: time,
            // Generate 5 sets of data with slight variations
            temp1: baseTemp + (Math.sin(i * 0.5) * 2) + Math.random() * 1.5,
            temp2: baseTemp + 1 + (Math.sin(i * 0.4) * 2.5) + Math.random() * 1.5,
            temp3: baseTemp - 2 + (Math.sin(i * 0.6) * 3) + Math.random() * 1.5,
            temp4: baseTemp + 3 + (Math.sin(i * 0.7) * 1.8) + Math.random() * 1.5,
            temp5: baseTemp - 1 + (Math.sin(i * 0.3) * 2.2) + Math.random() * 1.5,

            hum1: baseHum + (Math.sin(i * 0.5) * 5) + Math.random() * 3,
            hum2: baseHum + 3 + (Math.sin(i * 0.4) * 6) + Math.random() * 3,
            hum3: baseHum - 4 + (Math.sin(i * 0.6) * 7) + Math.random() * 3,
            hum4: baseHum + 5 + (Math.sin(i * 0.7) * 4) + Math.random() * 3,
            hum5: baseHum - 2 + (Math.sin(i * 0.3) * 5) + Math.random() * 3,

            light1: baseLight + (Math.sin(i * 0.5) * 50) + Math.random() * 20,
            light2: baseLight + 50 + (Math.sin(i * 0.4) * 60) + Math.random() * 20,
            light3: baseLight - 40 + (Math.sin(i * 0.6) * 70) + Math.random() * 20,
            light4: baseLight + 80 + (Math.sin(i * 0.7) * 40) + Math.random() * 20,
            light5: baseLight - 10 + (Math.sin(i * 0.3) * 50) + Math.random() * 20,
        });
    }
    return data;
};

// --- COMPONENTS ---

/**
 * Historical Trends View with 3 line charts (Temperature, Humidity, Lightness)
 */
const HistoricalTrendsView = ({ historicalData }) => {
    if (!historicalData || historicalData.length === 0) {
        return (
            <div className="flex items-center justify-center min-h-[50vh] p-8 text-xl text-yellow-400 border-2 border-dashed border-yellow-700 rounded-xl bg-gray-800/50">
                No Historical Records Found for this Period.
            </div>
        );
    }

    const ChartWrapper = ({ title, dataKeys, unit }) => (
        <div className="bg-gray-800 p-6 rounded-2xl shadow-xl transition duration-300 hover:shadow-2xl hover:bg-gray-700/80">
            <h3 className="text-xl font-semibold mb-4 text-white border-b border-gray-600 pb-2">{title}</h3>
            <ResponsiveContainer width="100%" height={300}>
                <LineChart data={historicalData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                    <XAxis dataKey="time" stroke="#9CA3AF" />
                    <YAxis stroke="#9CA3AF" domain={['auto', 'auto']} tickFormatter={(value) => `${value}${unit}`} />
                    <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #4B5563', color: '#E5E7EB' }} />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    {dataKeys.map((key, index) => (
                        <Line
                            key={key}
                            type="monotone"
                            dataKey={key}
                            name={`Sensor ${index + 1}`}
                            stroke={sensorColors[index]}
                            dot={false}
                            strokeWidth={2}
                            activeDot={{ r: 6 }}
                        />
                    ))}
                </LineChart>
            </ResponsiveContainer>
        </div>
    );

    return (
        <div className="space-y-8">
            <ChartWrapper
                title="Temperature Trends (°C)"
                dataKeys={['temp1', 'temp2', 'temp3', 'temp4', 'temp5']}
                unit="°C"
            />
            <ChartWrapper
                title="Humidity Trends (%)"
                dataKeys={['hum1', 'hum2', 'hum3', 'hum4', 'hum5']}
                unit="%"
            />
            <ChartWrapper
                title="Lightness Trends (lux)"
                dataKeys={['light1', 'light2', 'light3', 'light4', 'light5']}
                unit="lux"
            />
        </div>
    );
};

/**
 * Card component for a single sensor's live data
 */
const SensorCard = ({ sensor, onReset }) => {
    const isOffline = sensor.status === 'Offline';
    const color = sensorColors[sensor.id - 1];

    // Helper to format bar chart data for visualization
    const getBarData = (metric, maxVal) => [
        { name: metric, value: sensor.data ? sensor.data[metric] : 0, color: color }
    ];

    const valueClasses = 'text-3xl font-bold transition-all duration-500';

    return (
        <div
            className={`relative p-6 rounded-xl shadow-2xl transition-all duration-300 transform hover:scale-[1.02] 
      ${isOffline ? 'bg-gray-900 border-2 border-red-600/50 opacity-70' : 'bg-gray-800 border-t-4 border-l-2 border-opacity-70'}
      `}
            style={{ borderColor: isOffline ? '#DC2626' : color }}
        >
            <div className="flex justify-between items-start mb-4">
                <h3 className={`text-xl font-semibold ${isOffline ? 'text-red-400' : 'text-white'}`}>{sensor.name}</h3>
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${isOffline ? 'bg-red-800 text-red-100' : 'bg-green-700 text-green-100'}`}>
                    {sensor.status}
                </span>
            </div>

            {isOffline ? (
                <div className="text-center py-10">
                    <p className="text-red-500 text-lg font-medium mb-4">
                        Sensor Offline / No Data Received
                    </p>
                    <button
                        onClick={() => onReset(sensor.id)}
                        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition duration-150 shadow-md"
                    >
                        Attempt Reset
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-3 gap-4">
                    {/* Temperature */}
                    <div className="flex flex-col items-center">
                        <p className="text-gray-400 text-sm mb-1">Temp</p>
                        <div className={valueClasses} style={{ color: color }}>
                            {sensor.data.temperature.toFixed(1)}°C
                        </div>
                    </div>

                    {/* Humidity */}
                    <div className="flex flex-col items-center">
                        <p className="text-gray-400 text-sm mb-1">Humidity</p>
                        <div className={valueClasses} style={{ color: color }}>
                            {sensor.data.humidity.toFixed(0)}%
                        </div>
                    </div>

                    {/* Lightness */}
                    <div className="flex flex-col items-center">
                        <p className="text-gray-400 text-sm mb-1">Lightness</p>
                        <div className={valueClasses} style={{ color: color }}>
                            {sensor.data.lightness.toFixed(0)} lux
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

/**
 * Main application component.
 */
const App = () => {
    const [sensors, setSensors] = useState(initialSensors);
    const [currentView, setCurrentView] = useState('live'); // 'live' or 'history'
    const [historicalData, setHistoricalData] = useState(null);
    const [lastUpdateTime, setLastUpdateTime] = useState(new Date());

    // --- Mock API Call for Historical Data ---
    useEffect(() => {
        // Simulate fetching historical data
        const fetchHistoricalData = async () => {
            // Small delay to simulate network latency
            await new Promise(resolve => setTimeout(resolve, 500));
            // For the edge case demonstration, uncomment the line below:
            // if (Math.random() < 0.2) return []; // Returns empty array 20% of the time

            return generateHistoricalData();
        };

        if (currentView === 'history' && !historicalData) {
            fetchHistoricalData().then(data => {
                setHistoricalData(data);
            }).catch(console.error);
        }
    }, [currentView, historicalData]);

    // --- Mock WebSocket for Live Data ---
    useEffect(() => {
        if (currentView !== 'live') return;

        const interval = setInterval(() => {
            setSensors(prevSensors => prevSensors.map(sensor => {
                // Only update data if the sensor is not explicitly offline
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
            }));
            setLastUpdateTime(new Date());
        }, 2000); // Update every 2 seconds

        return () => clearInterval(interval); // Cleanup on unmount/view change
    }, [currentView]);

    // --- Handler for Resetting Failed Sensors ---
    const handleResetSensor = useCallback((id) => {
        setSensors(prevSensors => prevSensors.map(sensor => {
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
        }));
    }, []);

    const buttonClass = (view) => `px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-lg ${currentView === view
        ? 'bg-blue-600 text-white shadow-blue-500/50'
        : 'bg-gray-700 text-gray-300 hover:bg-blue-500 hover:text-white'
        }`;

    return (
        <div className="min-h-screen bg-gray-900 text-gray-100 p-4 sm:p-8 font-sans">
            <header className="mb-10 text-center">
                <h1 className="text-4xl font-extrabold text-white mb-2 tracking-tight">Multi-Sensor Dashboard</h1>
                <p className="text-gray-400">Real-time data visualization for 5 environment sensor sets.</p>
            </header>

            {/* Navigation */}
            <div className="flex justify-center space-x-4 mb-12">
                <button onClick={() => setCurrentView('live')} className={buttonClass('live')}>
                    Live Data
                </button>
                <button onClick={() => setCurrentView('history')} className={buttonClass('history')}>
                    Historical Trends
                </button>
            </div>

            {/* Content Area */}
            <main className="max-w-7xl mx-auto">
                {currentView === 'live' ? (
                    <>
                        <div className="flex justify-end text-sm text-gray-500 mb-4">
                            Last Update: {lastUpdateTime.toLocaleTimeString()}
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                            {sensors.map(sensor => (
                                <SensorCard key={sensor.id} sensor={sensor} onReset={handleResetSensor} />
                            ))}
                        </div>
                    </>
                ) : (
                    <HistoricalTrendsView historicalData={historicalData} />
                )}
            </main>

            <footer className="mt-12 text-center text-sm text-gray-600 border-t border-gray-800 pt-6">
                <p>Dashboard Powered by Mock WebSocket & API | Designed with Tailwind CSS & Recharts</p>
            </footer>
        </div>
    );
};

export default App;
