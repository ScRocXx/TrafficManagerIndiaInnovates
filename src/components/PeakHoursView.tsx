"use client";
import React, { useState, useRef, useCallback, useEffect } from "react";
import { Clock, Search, ArrowUpRight, ArrowDownRight, Wrench, Timer, Activity } from "lucide-react";
import { ProfileAlerts } from "./Overlays";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";

/* ── City-wide aggregate hourly data ── */
const cityWideData = [
  { hour: "6AM", vehicles: 12400 }, { hour: "7AM", vehicles: 31200 },
  { hour: "8AM", vehicles: 68500 }, { hour: "9AM", vehicles: 78200 },
  { hour: "10AM", vehicles: 54100 }, { hour: "11AM", vehicles: 42800 },
  { hour: "12PM", vehicles: 46200 }, { hour: "1PM", vehicles: 49500 },
  { hour: "2PM", vehicles: 44100 }, { hour: "3PM", vehicles: 47800 },
  { hour: "4PM", vehicles: 56200 }, { hour: "5PM", vehicles: 78900 },
  { hour: "6PM", vehicles: 88200 }, { hour: "7PM", vehicles: 74100 },
  { hour: "8PM", vehicles: 52300 }, { hour: "9PM", vehicles: 31200 },
  { hour: "10PM", vehicles: 19800 }, { hour: "11PM", vehicles: 11200 },
];

/* ── Per-intersection data ── */
interface IntersectionPeakData {
  id: string;
  name: string;
  status: "Red" | "Yellow" | "Green";
  peakHour: string;
  peakVolume: number;
  avgPValue: number;
  maxCongestionHrs: number;
  clearanceWindow: string;
  hourlyData: { hour: string; vehicles: number }[];
}

const intersectionData: IntersectionPeakData[] = [
  {
    id: "INT-01", name: "ITO Junction", status: "Red", peakHour: "6:15 PM",
    peakVolume: 14200, avgPValue: 0.85, maxCongestionHrs: 4.2, clearanceWindow: "11 PM – 5 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 1800 }, { hour: "8AM", vehicles: 6200 }, { hour: "10AM", vehicles: 4100 },
      { hour: "12PM", vehicles: 4800 }, { hour: "2PM", vehicles: 4200 }, { hour: "4PM", vehicles: 7800 },
      { hour: "6PM", vehicles: 14200 }, { hour: "8PM", vehicles: 8100 }, { hour: "10PM", vehicles: 2400 },
    ]
  },
  {
    id: "INT-02", name: "AIIMS", status: "Red", peakHour: "6:30 PM",
    peakVolume: 12800, avgPValue: 0.92, maxCongestionHrs: 3.8, clearanceWindow: "11 PM – 5 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 1500 }, { hour: "8AM", vehicles: 5800 }, { hour: "10AM", vehicles: 3900 },
      { hour: "12PM", vehicles: 4200 }, { hour: "2PM", vehicles: 3800 }, { hour: "4PM", vehicles: 7200 },
      { hour: "6PM", vehicles: 12800 }, { hour: "8PM", vehicles: 7600 }, { hour: "10PM", vehicles: 2100 },
    ]
  },
  {
    id: "INT-03", name: "Ashram Chowk", status: "Red", peakHour: "5:45 PM",
    peakVolume: 13500, avgPValue: 0.88, maxCongestionHrs: 4.0, clearanceWindow: "10:30 PM – 5:30 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 2100 }, { hour: "8AM", vehicles: 6800 }, { hour: "10AM", vehicles: 4500 },
      { hour: "12PM", vehicles: 5100 }, { hour: "2PM", vehicles: 4600 }, { hour: "4PM", vehicles: 8200 },
      { hour: "6PM", vehicles: 13500 }, { hour: "8PM", vehicles: 7900 }, { hour: "10PM", vehicles: 2800 },
    ]
  },
  {
    id: "INT-04", name: "Connaught Place", status: "Yellow", peakHour: "1:00 PM",
    peakVolume: 9100, avgPValue: 0.60, maxCongestionHrs: 2.5, clearanceWindow: "9 PM – 6 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 900 }, { hour: "8AM", vehicles: 3200 }, { hour: "10AM", vehicles: 5100 },
      { hour: "12PM", vehicles: 8200 }, { hour: "2PM", vehicles: 7100 }, { hour: "4PM", vehicles: 5800 },
      { hour: "6PM", vehicles: 9100 }, { hour: "8PM", vehicles: 4200 }, { hour: "10PM", vehicles: 1800 },
    ]
  },
  {
    id: "INT-05", name: "South Ext", status: "Red", peakHour: "6:00 PM",
    peakVolume: 10500, avgPValue: 0.75, maxCongestionHrs: 3.2, clearanceWindow: "10 PM – 5 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 1200 }, { hour: "8AM", vehicles: 4500 }, { hour: "10AM", vehicles: 3600 },
      { hour: "12PM", vehicles: 4100 }, { hour: "2PM", vehicles: 3900 }, { hour: "4PM", vehicles: 6200 },
      { hour: "6PM", vehicles: 10500 }, { hour: "8PM", vehicles: 5800 }, { hour: "10PM", vehicles: 2000 },
    ]
  },
  {
    id: "INT-06", name: "Kashmere Gate", status: "Yellow", peakHour: "9:00 AM",
    peakVolume: 8700, avgPValue: 0.55, maxCongestionHrs: 2.1, clearanceWindow: "8 PM – 6 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 2800 }, { hour: "8AM", vehicles: 7200 }, { hour: "10AM", vehicles: 8700 },
      { hour: "12PM", vehicles: 5400 }, { hour: "2PM", vehicles: 4800 }, { hour: "4PM", vehicles: 5600 },
      { hour: "6PM", vehicles: 6200 }, { hour: "8PM", vehicles: 3100 }, { hour: "10PM", vehicles: 1200 },
    ]
  },
  {
    id: "INT-07", name: "Raja Garden", status: "Red", peakHour: "5:30 PM",
    peakVolume: 11900, avgPValue: 0.78, maxCongestionHrs: 3.5, clearanceWindow: "10 PM – 5:30 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 1600 }, { hour: "8AM", vehicles: 5200 }, { hour: "10AM", vehicles: 4000 },
      { hour: "12PM", vehicles: 4600 }, { hour: "2PM", vehicles: 4200 }, { hour: "4PM", vehicles: 7400 },
      { hour: "6PM", vehicles: 11900 }, { hour: "8PM", vehicles: 6800 }, { hour: "10PM", vehicles: 2200 },
    ]
  },
  {
    id: "INT-08", name: "Karol Bagh", status: "Yellow", peakHour: "7:00 PM",
    peakVolume: 7200, avgPValue: 0.45, maxCongestionHrs: 1.8, clearanceWindow: "9 PM – 6:30 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 800 }, { hour: "8AM", vehicles: 2800 }, { hour: "10AM", vehicles: 3200 },
      { hour: "12PM", vehicles: 4100 }, { hour: "2PM", vehicles: 3800 }, { hour: "4PM", vehicles: 5200 },
      { hour: "6PM", vehicles: 7200 }, { hour: "8PM", vehicles: 4800 }, { hour: "10PM", vehicles: 1600 },
    ]
  },
  {
    id: "INT-09", name: "Dhaula Kuan", status: "Green", peakHour: "5:00 PM",
    peakVolume: 5200, avgPValue: 0.25, maxCongestionHrs: 1.0, clearanceWindow: "8 PM – 7 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 600 }, { hour: "8AM", vehicles: 2200 }, { hour: "10AM", vehicles: 2800 },
      { hour: "12PM", vehicles: 3100 }, { hour: "2PM", vehicles: 2900 }, { hour: "4PM", vehicles: 4200 },
      { hour: "6PM", vehicles: 5200 }, { hour: "8PM", vehicles: 3400 }, { hour: "10PM", vehicles: 1100 },
    ]
  },
  {
    id: "INT-10", name: "Laxmi Nagar", status: "Green", peakHour: "8:30 AM",
    peakVolume: 5800, avgPValue: 0.30, maxCongestionHrs: 1.2, clearanceWindow: "8 PM – 7 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 1200 }, { hour: "8AM", vehicles: 5800 }, { hour: "10AM", vehicles: 3400 },
      { hour: "12PM", vehicles: 2800 }, { hour: "2PM", vehicles: 2600 }, { hour: "4PM", vehicles: 3800 },
      { hour: "6PM", vehicles: 4200 }, { hour: "8PM", vehicles: 2400 }, { hour: "10PM", vehicles: 900 },
    ]
  },
  {
    id: "INT-11", name: "Moolchand", status: "Green", peakHour: "6:45 PM",
    peakVolume: 4100, avgPValue: 0.20, maxCongestionHrs: 0.8, clearanceWindow: "7 PM – 7 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 500 }, { hour: "8AM", vehicles: 1800 }, { hour: "10AM", vehicles: 2200 },
      { hour: "12PM", vehicles: 2600 }, { hour: "2PM", vehicles: 2400 }, { hour: "4PM", vehicles: 3200 },
      { hour: "6PM", vehicles: 4100 }, { hour: "8PM", vehicles: 2800 }, { hour: "10PM", vehicles: 800 },
    ]
  },
  {
    id: "INT-12", name: "Akshardham", status: "Green", peakHour: "9:15 AM",
    peakVolume: 3600, avgPValue: 0.15, maxCongestionHrs: 0.5, clearanceWindow: "7 PM – 7 AM",
    hourlyData: [
      { hour: "6AM", vehicles: 800 }, { hour: "8AM", vehicles: 3200 }, { hour: "10AM", vehicles: 3600 },
      { hour: "12PM", vehicles: 2400 }, { hour: "2PM", vehicles: 2100 }, { hour: "4PM", vehicles: 2800 },
      { hour: "6PM", vehicles: 3200 }, { hour: "8PM", vehicles: 1800 }, { hour: "10PM", vehicles: 600 },
    ]
  },
];

/* eslint-disable @typescript-eslint/no-explicit-any */
function CustomTooltip({ active, payload, label, isDark }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-[11px] text-gray-500 dark:text-slate-400 font-mono">{label}</p>
      <p className="text-sm font-bold text-gray-900 dark:text-white">
        {Number(payload[0].value).toLocaleString()}{" "}
        <span className="text-gray-500 dark:text-slate-400 font-normal text-xs">vehicles</span>
      </p>
    </div>
  );
}

export default function PeakHoursView({ setActiveTab }: { setActiveTab?: (tab: string) => void }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [isDark, setIsDark] = useState(false);
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    // Check initial dark mode state
    setIsDark(document.documentElement.classList.contains("dark"));

    // Set up a mutation observer to watch for dark mode toggle
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "class") {
          setIsDark(document.documentElement.classList.contains("dark"));
        }
      });
    });

    observer.observe(document.documentElement, { attributes: true });

    return () => observer.disconnect();
  }, []);

  const setCardRef = useCallback((id: string) => (el: HTMLDivElement | null) => {
    cardRefs.current[id] = el;
  }, []);

  const scrollToCard = (id: string) => {
    const el = cardRefs.current[id];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.classList.add("ring-2", isDark ? "ring-cyan-500/50" : "ring-sky-500/50");
      setTimeout(() => el.classList.remove("ring-2", isDark ? "ring-cyan-500/50" : "ring-sky-500/50"), 2000);
    }
  };

  const filtered = intersectionData.filter(i =>
    i.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sidebarFiltered = intersectionData.filter(i =>
    i.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getPrimaryColor = () => isDark ? "#ef4444" : "#0ea5e9";

  const getBarColor = (status: string) => {
    if (status === "Red") return isDark ? "#ef4444" : "#0ea5e9";
    if (status === "Yellow") return "#f59e0b";
    if (status === "Green") return isDark ? "#64748b" : "#94a3b8";
    return "#64748b";
  };

  const STATUS_PILL: Record<string, string> = {
    Red: "bg-sky-100 text-sky-700 border-sky-200 dark:bg-red-500/15 dark:text-red-400 dark:border-red-500/30",
    Yellow: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/30",
    Green: "bg-gray-100 text-gray-700 border-gray-200 dark:bg-slate-500/15 dark:text-slate-400 dark:border-slate-500/30",
  };

  const STATUS_DOT: Record<string, string> = {
    Red: "bg-sky-500 dark:bg-red-500",
    Yellow: "bg-amber-500",
    Green: "bg-gray-400 dark:bg-slate-500",
  };

  return (
    <div className="w-full h-full flex overflow-hidden bg-gray-50 dark:bg-slate-950 transition-colors duration-300 relative">
      {/* Profile & Notification Buttons */}
      <ProfileAlerts setActiveTab={setActiveTab} className="absolute top-2 right-6" />

      {/* ── Main Column (75%) ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* ── City-Wide Aggregate (Fixed Top) ── */}
        <div className="flex-shrink-0 p-6 pb-0">
          <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-6 transition-colors duration-300 shadow-sm dark:shadow-none">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center transition-colors">
                  <Activity className="w-5 h-5 text-gray-500 dark:text-slate-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white">City-Wide Traffic Volume</h2>
                  <p className="text-xs text-gray-500 dark:text-slate-500 font-mono">Delhi NCR · All 12 Monitored Nodes · Today</p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="text-right">
                  <p className="text-[10px] text-gray-500 dark:text-slate-500 uppercase tracking-wider">Peak</p>
                  <p className="text-sky-600 dark:text-red-400 font-bold font-mono">88,200 <span className="text-gray-500 dark:text-slate-500 font-normal">@ 6 PM</span></p>
                </div>
                <div className="w-px h-8 bg-gray-200 dark:bg-slate-800" />
                <div className="text-right">
                  <p className="text-[10px] text-gray-500 dark:text-slate-500 uppercase tracking-wider">Avg</p>
                  <p className="text-gray-700 dark:text-slate-300 font-bold font-mono">47,230</p>
                </div>
              </div>
            </div>
            <div className="h-[180px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cityWideData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={getPrimaryColor()} stopOpacity={0.3} />
                      <stop offset="100%" stopColor={getPrimaryColor()} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#1e293b" : "#e2e8f0"} />
                  <XAxis dataKey="hour" tick={{ fill: isDark ? '#64748b' : '#94a3b8', fontSize: 10 }} axisLine={{ stroke: isDark ? '#1e293b' : '#e2e8f0' }} tickLine={false} />
                  <YAxis tick={{ fill: isDark ? '#64748b' : '#94a3b8', fontSize: 10 }} axisLine={{ stroke: isDark ? '#1e293b' : '#e2e8f0' }} tickLine={false} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip content={<CustomTooltip isDark={isDark} />} />
                  <Area type="monotone" dataKey="vehicles" stroke={getPrimaryColor()} strokeWidth={2} fill="url(#areaGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* ── Scrollable Intersection Cards ── */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <p className="text-[10px] text-gray-500 dark:text-slate-500 uppercase tracking-widest font-semibold mb-2">Individual Node Analysis · {filtered.length} Intersections</p>
          {filtered.map((item) => (
            <div
              key={item.id}
              ref={setCardRef(item.id)}
              className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-5 transition-all duration-300 shadow-sm dark:shadow-none"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${STATUS_DOT[item.status]}`} />
                  <div>
                    <h3 className="text-sm font-bold text-gray-900 dark:text-white">{item.name}</h3>
                    <p className="text-[11px] text-gray-500 dark:text-slate-500 font-mono">Node [{item.id}] · Peak at {item.peakHour}</p>
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${STATUS_PILL[item.status]}`}>
                  {item.status === 'Red' ? 'Critical' : item.status === 'Yellow' ? 'Moderate' : 'Normal'}
                </span>
              </div>

              <div className="flex gap-5">
                {/* Bar Chart */}
                <div className="flex-1 h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={item.hourlyData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#1e293b" : "#e2e8f0"} vertical={false} />
                      <XAxis dataKey="hour" tick={{ fill: isDark ? '#475569' : '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: isDark ? '#475569' : '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
                      <Tooltip content={<CustomTooltip isDark={isDark} />} />
                      <Bar dataKey="vehicles" fill={getBarColor(item.status)} radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* MCD Metrics */}
                <div className="w-[200px] flex flex-col gap-2.5 flex-shrink-0">
                  <div className="bg-gray-50 dark:bg-slate-800/50 rounded-lg p-3 border border-gray-100 dark:border-slate-700/30 transition-colors">
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-slate-500 uppercase tracking-wider mb-1">
                      <Timer className="w-3 h-3" />
                      Max Congestion
                    </div>
                    <p className="text-lg font-bold text-gray-900 dark:text-white font-mono">{item.maxCongestionHrs} <span className="text-xs text-gray-500 dark:text-slate-500 font-normal">hrs</span></p>
                  </div>
                  <div className="bg-gray-50 dark:bg-slate-800/50 rounded-lg p-3 border border-gray-100 dark:border-slate-700/30 transition-colors">
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-slate-500 uppercase tracking-wider mb-1">
                      <Wrench className="w-3 h-3" />
                      Clearance Window
                    </div>
                    <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 font-mono">{item.clearanceWindow}</p>
                  </div>
                  <div className="bg-gray-50 dark:bg-slate-800/50 rounded-lg p-3 border border-gray-100 dark:border-slate-700/30 transition-colors">
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-slate-500 uppercase tracking-wider mb-1">
                      <Activity className="w-3 h-3" />
                      Avg P-Value
                    </div>
                    <p className="text-lg font-bold font-mono" style={{ color: getBarColor(item.status) }}>{item.avgPValue.toFixed(2)}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right Sidebar (25%, Sticky) ── */}
      <div className="w-[280px] flex-shrink-0 h-full border-l border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 flex flex-col transition-colors">
        <div className="p-4 border-b border-gray-200 dark:border-slate-800">
          <p className="text-[11px] text-gray-500 dark:text-slate-500 uppercase tracking-widest font-semibold mb-3 mt-10">Quick Find</p>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search nodes..."
              className="w-full pl-9 pr-3 py-2.5 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 outline-none focus:ring-1 focus:ring-sky-500 dark:focus:ring-slate-600 transition-all font-mono"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {sidebarFiltered.map(item => (
            <button
              key={item.id}
              onClick={() => scrollToCard(item.id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors group text-left"
            >
              <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${STATUS_DOT[item.status]}`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-700 dark:text-slate-300 font-medium truncate group-hover:text-gray-900 dark:group-hover:text-white transition-colors">{item.name}</p>
                <p className="text-[10px] text-gray-500 dark:text-slate-600 font-mono">P: {item.avgPValue.toFixed(2)} · {item.peakHour}</p>
              </div>
              <span className={`w-1.5 h-5 rounded-full flex-shrink-0 ${STATUS_DOT[item.status]} opacity-20 dark:opacity-30`} />
            </button>
          ))}
          {sidebarFiltered.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-slate-600 text-center py-8">No nodes found</p>
          )}
        </div>

        {/* Sidebar Footer Stats */}
        <div className="p-4 border-t border-gray-200 dark:border-slate-800 space-y-2">
          <div className="flex justify-between text-[11px]">
            <span className="text-gray-500 dark:text-slate-500">Critical Nodes</span>
            <span className="text-sky-600 dark:text-red-400 font-bold font-mono">{intersectionData.filter(i => i.status === 'Red').length}</span>
          </div>
          <div className="flex justify-between text-[11px]">
            <span className="text-gray-500 dark:text-slate-500">Moderate</span>
            <span className="text-amber-500 dark:text-amber-400 font-bold font-mono">{intersectionData.filter(i => i.status === 'Yellow').length}</span>
          </div>
          <div className="flex justify-between text-[11px]">
            <span className="text-gray-500 dark:text-slate-500">Normal Flow</span>
            <span className="text-gray-400 dark:text-slate-400 font-bold font-mono">{intersectionData.filter(i => i.status === 'Green').length}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
