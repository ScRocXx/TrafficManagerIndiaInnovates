"use client";
import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { Camera, MapPin, AlertCircle, Clock, Navigation } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import { SearchBar, ProfileAlerts } from '@/components/Overlays';

const MapComponent = dynamic(
  () => import('@/components/MapComponent'),
  { ssr: false }
);

export const vulnerabilitiesData = [
  {
    id: "CAM-001",
    type: "Camera",
    location: "Connaught Place",
    coordinates: [28.6328, 77.2197],
    status: "Critical",
    issue: "Lens Shattered",
    last_ping: "2026-03-23T10:05:00Z"
  },
  {
    id: "RAD-042",
    type: "Radar Sensor",
    location: "AIIMS Intersection",
    coordinates: [28.5672, 77.2100],
    status: "Warning",
    issue: "Intermittent Signal",
    last_ping: "2026-03-23T09:45:00Z"
  },
  {
    id: "LGT-088",
    type: "Traffic Light",
    location: "South Ext",
    coordinates: [28.5684, 77.2201],
    status: "Critical",
    issue: "Power Failure",
    last_ping: "2026-03-23T08:30:00Z"
  },
  {
    id: "CAM-104",
    type: "Camera",
    location: "ITO Junction",
    coordinates: [28.6295, 77.2405],
    status: "Warning",
    issue: "Connection Timeout",
    last_ping: "2026-03-23T10:15:00Z"
  },
  {
    id: "SEN-211",
    type: "Air Quality Sensor",
    location: "Karol Bagh",
    coordinates: [28.6520, 77.1903],
    status: "Critical",
    issue: "Sensor Contaminated",
    last_ping: "2026-03-23T07:12:00Z"
  },
  {
    id: "CAM-302",
    type: "Camera",
    location: "Lajpat Nagar",
    coordinates: [28.5680, 77.2433],
    status: "Warning",
    issue: "Poor Visibility (Dust)",
    last_ping: "2026-03-23T09:55:00Z"
  }
];

function PeakHoursView() {
  const hours = [
    '6A', '7A', '8A', '9A', '10A', '11A', '12P',
    '1P', '2P', '3P', '4P', '5P', '6P', '7P', '8P', '9P', '10P'
  ];
  // Mock traffic data (0-100) representing "screen time" density
  const trafficData = [
    10, 20, 60, 95, 80, 50, 45,
    40, 45, 50, 60, 85, 95, 75, 55, 30, 15
  ];

  return (
    <div className="p-8 h-full flex flex-col items-center justify-center overflow-y-auto w-full">
      <div className="w-full max-w-4xl bg-white dark:bg-slate-800 rounded-3xl shadow-xl p-8">
        <h2 className="text-2xl font-bold mb-2 text-gray-800 dark:text-white">Peak Hours Analysis</h2>
        <p className="text-gray-500 mb-8">Screen time style view of traffic density</p>

        <div className="flex items-end justify-between h-64 gap-2">
          {hours.map((hour, i) => (
            <div key={i} className="flex flex-col items-center w-full group">
              <div className="h-48 w-full flex items-end justify-center rounded-t-lg mb-2 relative">
                {/* Tooltip */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-10 bg-gray-800 text-white text-xs py-1 px-2 rounded">
                  {trafficData[i]}%
                </div>
                <div
                  className={`w-full max-w-[40px] rounded-t-lg transition-all duration-500 ${trafficData[i] > 80 ? 'bg-red-500' :
                    trafficData[i] > 50 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                  style={{ height: `${trafficData[i]}%` }}
                ></div>
              </div>
              <span className="text-xs text-gray-500">{hour}</span>
            </div>
          ))}
        </div>
        <div className="flex justify-center items-center space-x-6 mt-8 border-t pt-4 dark:border-slate-700">
          <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-green-500 mr-2"></div><span className="text-sm">Low</span></div>
          <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></div><span className="text-sm">Moderate</span></div>
          <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div><span className="text-sm">High</span></div>
        </div>
      </div>
    </div>
  );
}

function MostBusiestView() {
  const cities = [
    'Connaught Place', 'Karol Bagh', 'Lajpat Nagar', 'Dwarka',
    'Rohini', 'Vasant Kunj', 'Saket', 'Nehru Place', 'Hauz Khas', 'Chandni Chowk'
  ];

  // Create a randomized ranking list using useMemo to avoid re-shuffling on every render
  const rankedCities = React.useMemo(() => {
    const list = cities.map(city => ({
      name: city,
      trafficIndex: Math.floor(Math.random() * 50) + 50 // Random number between 50 and 99
    }));
    list.sort((a, b) => b.trafficIndex - a.trafficIndex);
    return list;
  }, []);

  return (
    <div className="p-8 h-full flex flex-col items-center overflow-y-auto w-full">
      <div className="w-full max-w-3xl bg-white dark:bg-slate-800 rounded-3xl shadow-xl p-8 my-auto">
        <h2 className="text-2xl font-bold mb-2 text-gray-800 dark:text-white">Most Busiest Areas</h2>
        <p className="text-gray-500 mb-8">Real-time ranking of Delhi areas by randomly generated traffic density</p>

        <div className="space-y-4">
          {rankedCities.map((city, index) => (
            <div key={city.name} className="flex items-center bg-gray-50 dark:bg-slate-700/50 p-4 rounded-xl hover:shadow-md transition-shadow">
              <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center font-bold text-blue-600 dark:text-blue-400 mr-4">
                #{index + 1}
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 dark:text-white text-lg">{city.name}</h3>
                <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-2 mt-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${city.trafficIndex}%` }}
                  ></div>
                </div>
              </div>
              <div className="ml-4 text-right">
                <span className="block text-2xl font-bold text-gray-800 dark:text-white">{city.trafficIndex}</span>
                <span className="text-xs text-gray-500 uppercase">Index</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function HardwareVulnerabilityView() {
  return (
    <div className="p-8 h-full flex flex-col items-center overflow-y-auto w-full">
      <div className="w-full max-w-6xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Hardware Vulnerability</h2>
            <p className="text-gray-500">Live monitoring of device health across the city</p>
          </div>
          <span className="px-4 py-2 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 font-semibold rounded-full text-sm">
            {vulnerabilitiesData.length} Issues Detected
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {vulnerabilitiesData.map((vulnerabilityData) => (
            <div id={`vuln-${vulnerabilityData.id}`} key={vulnerabilityData.id} className="bg-white dark:bg-slate-800 rounded-3xl shadow-sm border border-gray-100 dark:border-slate-700/50 p-6 flex flex-col hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex flex-col">
                  <div className="flex items-center text-gray-800 dark:text-white font-semibold mb-1">
                    {vulnerabilityData.type === 'Camera' ? <Camera className="w-4 h-4 mr-2 text-gray-500" /> : <Navigation className="w-4 h-4 mr-2 text-gray-500" />}
                    {vulnerabilityData.type}
                  </div>
                  <span className="text-xs text-gray-500">{vulnerabilityData.id}</span>
                </div>
                <span className={`px-3 py-1 font-semibold rounded-full text-xs flex items-center ${vulnerabilityData.status === 'Critical'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                  }`}>
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {vulnerabilityData.status}
                </span>
              </div>

              <div className="flex-1 space-y-4">
                <div className={`p-3 rounded-xl border ${vulnerabilityData.status === 'Critical'
                  ? 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-900/30'
                  : 'bg-yellow-50 dark:bg-yellow-900/10 border-yellow-100 dark:border-yellow-900/30'
                  }`}>
                  <div className={`text-xs mb-1 ${vulnerabilityData.status === 'Critical' ? 'text-red-500 dark:text-red-400' : 'text-yellow-600 dark:text-yellow-500'
                    }`}>Detected Issue</div>
                  <div className={`font-semibold text-sm ${vulnerabilityData.status === 'Critical' ? 'text-red-700 dark:text-red-400' : 'text-yellow-800 dark:text-yellow-500'
                    }`}>
                    {vulnerabilityData.issue}
                  </div>
                </div>

                <div className="flex space-x-4">
                  <div className="flex-1">
                    <div className="text-xs text-gray-500 mb-1 flex items-center">
                      <MapPin className="w-3 h-3 mr-1" /> Location
                    </div>
                    <div className="text-sm font-medium text-gray-800 dark:text-white truncate">
                      {vulnerabilityData.location}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1 flex items-center">
                      <Navigation className="w-3 h-3 mr-1" /> Coordinates
                    </div>
                    <div className="text-sm font-medium text-gray-800 dark:text-white truncate">
                      {vulnerabilityData.coordinates[0]}, {vulnerabilityData.coordinates[1]}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-gray-100 dark:border-slate-700 flex items-center justify-between text-gray-500 dark:text-gray-400 text-xs">
                <div className="flex items-center">
                  <Clock className="w-3 h-3 mr-1" />
                  <span>{new Date(vulnerabilityData.last_ping).toLocaleTimeString()}</span>
                </div>
                <div className="flex gap-3">
                  <button className="text-blue-600 dark:text-blue-400 hover:text-blue-700 hover:underline font-semibold">
                    Dispatch
                  </button>
                  <button className="text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white hover:underline font-semibold">
                    View feed
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [activeTab, setActiveTab] = useState("Delhi Map");

  return (
    <main className="flex h-screen w-screen overflow-hidden bg-white dark:bg-slate-950 text-gray-900 dark:text-gray-100 transition-colors">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="flex-1 relative bg-gray-50 dark:bg-slate-900 transition-colors h-full flex flex-col">
        {activeTab === "Delhi Map" && (
          <>
            <SearchBar />
            <ProfileAlerts setActiveTab={setActiveTab} />
            <div className="flex-1 relative w-full h-full">
              <MapComponent />
            </div>
          </>
        )}
        {activeTab === "Peak hours" && <PeakHoursView />}
        {activeTab === "Most busiest" && <MostBusiestView />}
        {activeTab === "Hardware vulnerability" && <HardwareVulnerabilityView />}
      </div>
    </main>
  );
}
