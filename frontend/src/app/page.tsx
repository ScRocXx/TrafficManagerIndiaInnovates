"use client";
import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import Sidebar from '@/components/Sidebar';
import { SearchBar, ProfileAlerts } from '@/components/Overlays';
import PeakHoursView from '@/components/PeakHoursView';
import MostBusiestView from '@/components/MostBusiestView';
import HardwareVulnerabilityView from '@/components/HardwareVulnerabilityView';
import { X } from 'lucide-react';
import type { IntersectionData } from '@/lib/intersections';

export type { IntersectionData } from '@/lib/intersections';

export const vulnerabilitiesData = [
  {
    id: "V001",
    type: "Camera Offline",
    status: "Critical",
    last_ping: "2026-03-24T04:25:00.000Z",
    issue: "Connection timeout",
    location: "ITO Junction"
  },
  {
    id: "V002",
    type: "High Latency",
    status: "Yellow",
    last_ping: "2026-03-24T04:15:00.000Z",
    issue: "Network congestion detected",
    location: "AIIMS Intersection"
  },
  {
    id: "V003",
    type: "Sensor Malfunction",
    status: "Critical",
    last_ping: "2026-03-24T03:45:00.000Z",
    issue: "Inductive loop failure",
    location: "Ashram Chowk"
  },
  {
    id: "V004",
    type: "Signal Controller Error",
    status: "Yellow",
    last_ping: "2026-03-24T04:22:00.000Z",
    issue: "Phase timing desync",
    location: "Connaught Place"
  }
];

const MapComponent = dynamic(
  () => import('@/components/MapComponent'),
  { ssr: false }
);

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function Home() {
  const [selectedIntersection, setSelectedIntersection] = useState<IntersectionData | null>(null);
  const [activeTab, setActiveTab] = useState("Delhi Map");
  const [focusIntersection, setFocusIntersection] = useState<string | null>(null);
  
  // State for live selected intersection data
  const [liveData, setLiveData] = useState<{status: string, p: number} | null>(null);

  // Poll for live data when an intersection is selected
  useEffect(() => {
    if (!selectedIntersection) {
      setLiveData(null);
      return;
    }
    
    const fetchLive = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://india-innovate-backend.onrender.com";
        const res = await fetch(`${API_URL}/api/traffic`);
        if (!res.ok) return;
        const data: any[] = await res.json();
        const liveMatch = data.find((d: any) => d.nodeId === selectedIntersection.nodeId);
        if (liveMatch) {
          setLiveData({
            status: liveMatch.status || "Green",
            p: liveMatch.congestionLevel || 0
          });
        }
      } catch (e) {
        console.error("Failed to fetch live intersection details", e);
      }
    };
    
    fetchLive();
    const interval = setInterval(fetchLive, 5000);
    return () => clearInterval(interval);
  }, [selectedIntersection]);

  const handleSearchSelect = (name: string) => {
    setActiveTab("Delhi Map");
    setSelectedIntersection(null);
    setFocusIntersection(name);
  };

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    if (tab !== "Delhi Map") {
      setSelectedIntersection(null);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case "Peak hours":
        return <PeakHoursView setActiveTab={handleTabChange} />;
      case "Most busiest":
        return <MostBusiestView setActiveTab={handleTabChange} />;
      case "Hardware vulnerability":
        return <HardwareVulnerabilityView setActiveTab={handleTabChange} />;
      case "Delhi Map":
      default:
        const currentStatus = liveData ? liveData.status : (selectedIntersection?.status || "Green");
        const currentP = liveData ? liveData.p.toFixed(2) : (selectedIntersection?.p.toFixed(2) || "0.00");
        
        return (
          <>
            {selectedIntersection && (
              <div className="w-[50%] h-full border-r border-gray-200 bg-white flex flex-col transition-all duration-300 relative z-10 anim-dashboard-open">
                <style dangerouslySetInnerHTML={{ __html: `
                  @keyframes dashboardOpenPulse {
                    0% { box-shadow: inset 0 0 0 4px transparent, 0 0 0 0 rgba(59,130,246,0); transform: translateX(-20px); opacity: 0; }
                    30% { transform: translateX(0); opacity: 1; }
                    40% { box-shadow: inset 0 0 0 4px rgba(59,130,246,0.5), 0 0 20px 10px rgba(59,130,246,0.3); }
                    100% { box-shadow: inset 0 0 0 4px transparent, 0 0 0 0 rgba(59,130,246,0); }
                  }
                  .anim-dashboard-open {
                    animation: dashboardOpenPulse 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                  }
                `}} />
                <div className="p-6 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{selectedIntersection.name}</h2>
                    <p className="text-sm text-gray-500">Node [{selectedIntersection.nodeId}] · Live Dashboard &amp; Camera Feed</p>
                  </div>
                  <button
                    onClick={() => setSelectedIntersection(null)}
                    className="p-2 bg-gray-200 rounded-full hover:bg-gray-300 transition text-gray-600"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="flex-1 p-6 flex flex-col gap-6 overflow-y-auto">
                  <div className="w-full aspect-video bg-gray-900 rounded-xl flex items-center justify-center relative overflow-hidden shadow-inner group relative">
                    {/* Simulated RTSP Live Traffic Feed using a 24/7 public intersection stream */}
                    <iframe
                      src={`https://www.youtube.com/embed/${selectedIntersection.videoId || "1EiC9bvVGnk"}?autoplay=1&mute=1&loop=1&playlist=${selectedIntersection.videoId || "1EiC9bvVGnk"}&controls=0&disablekb=1&fs=0&modestbranding=1`}
                      className="absolute inset-0 w-full h-full scale-[1.3] pointer-events-none opacity-90 group-hover:opacity-100 transition-opacity"
                      allow="autoplay; encrypted-media"
                    />
                    <div className="absolute top-4 left-4 flex gap-2 items-center z-10 bg-black/50 px-3 py-1.5 rounded-full backdrop-blur-sm border border-white/10">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_10px_rgba(239,68,68,1)]"></span>
                      <span className="text-[10px] text-white uppercase tracking-wider font-bold">Live RTSP Feed</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                      <p className="text-sm text-gray-500 mb-2 font-medium">Status</p>
                      <p className="font-bold text-xl text-gray-900 flex items-center gap-2">
                        <span className={`w-3.5 h-3.5 rounded-full ${currentStatus === 'Red' ? 'bg-red-500' : currentStatus === 'Yellow' ? 'bg-amber-400' : 'bg-slate-400'}`}></span>
                        {currentStatus === 'Green' ? 'Normal' : currentStatus === 'Yellow' ? 'Moderate' : 'Heavy'}
                      </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                      <p className="text-sm text-gray-500 mb-2 font-medium">P-Value</p>
                      <p className="font-bold text-xl text-gray-900">{currentP}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div className={`${selectedIntersection ? 'w-[50%]' : 'w-full'} h-full relative transition-all duration-300`}>
              <div className="absolute top-6 inset-x-6 z-[1000] flex items-start justify-between gap-4 pointer-events-none">
                <div className="flex-1 hidden md:block" />
                <div className="pointer-events-auto w-full max-w-[400px]">
                  <SearchBar onSelect={handleSearchSelect} className="w-full" />
                </div>
                <div className="flex-1 flex justify-end pointer-events-auto">
                  <ProfileAlerts setActiveTab={handleTabChange} className="" />
                </div>
              </div>
              <MapComponent
                onSelectIntersection={setSelectedIntersection}
                selectedIntersection={selectedIntersection}
                focusIntersection={focusIntersection}
                onFocusHandled={() => setFocusIntersection(null)}
              />
            </div>
          </>
        );
    }
  };

  return (
    <main className="flex h-screen w-screen overflow-hidden bg-white dark:bg-slate-950 text-gray-900 dark:text-slate-100 transition-colors">
      <Sidebar activeTab={activeTab} setActiveTab={handleTabChange} />
      <div className="flex-1 flex overflow-hidden relative">
        {renderContent()}
      </div>
    </main>
  );
}
