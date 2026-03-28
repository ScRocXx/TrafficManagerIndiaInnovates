"use client";
import React, { useState, useRef, useCallback, useEffect } from "react";
import { Clock, Search, ArrowUpRight, ArrowDownRight, Wrench, Timer, Activity } from "lucide-react";
import { ProfileAlerts } from "./Overlays";
import { useNetworkStatus, PEAK_TIMES, MAX_CONGESTION_MINS } from "@/hooks/useNetworkStatus";
import {
  AreaChart, Area, BarChart, Bar, Cell,
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
  savedCO2: number;
  timeSaved: number;
  maxCongestionHrs: number;
  clearanceWindow: string;
  hourlyData: { hour: string; density: number }[];
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function CustomTooltip({ active, payload, label, isDark, unit = "% density", isVolume = false }: any) {
  if (!active || !payload?.length) return null;
  const val = Number(payload[0].value);
  const displayVal = isVolume ? val.toLocaleString() : val.toFixed(1);
  return (
    <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-[11px] text-gray-500 dark:text-slate-400 font-mono">{label}</p>
      <p className="text-sm font-bold text-gray-900 dark:text-white">
        {displayVal}{" "}
        <span className="text-gray-500 dark:text-slate-400 font-normal text-xs">{unit}</span>
      </p>
    </div>
  );
}

export default function PeakHoursView({ setActiveTab }: { setActiveTab?: (tab: string) => void }) {
  const { nodes, intersections } = useNetworkStatus();
  const [searchTerm, setSearchTerm] = useState("");
  const [isDark, setIsDark] = useState(false);
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // ── Cumulative CO₂ & Time Saved (same model as MapComponent) ──
  const co2AccumRef = useRef(0);
  const timeSavedAccumRef = useRef(0);
  const [totalCO2, setTotalCO2] = useState(0);
  const [totalTimeSaved, setTotalTimeSaved] = useState(0);

  useEffect(() => {
    const now = new Date();
    const hoursToday = now.getHours() + now.getMinutes() / 60;
    co2AccumRef.current = hoursToday * 900;
    timeSavedAccumRef.current = hoursToday * 0.5;
  }, []);

  useEffect(() => {
    if (nodes.length === 0) return;
    const ticker = setInterval(() => {
      let rateKgPerSec = 0;
      nodes.forEach((node) => {
        if (!node || !node.lanes) return;
        const laneValues = Object.values(node.lanes) as { density: number; wait_time: number }[];
        const laneCount = laneValues.length || 1;
        const avgDensity = laneValues.reduce((s, l) => s + (l.density || 0), 0) / laneCount;
        const avgWait = laneValues.reduce((s, l) => s + (l.wait_time || 0), 0) / laneCount;
        const vehiclesPerLane = (avgDensity / 100) * 120;
        const savedIdleSec = avgWait * 0.18;
        const co2Grams = savedIdleSec * vehiclesPerLane * 2.3 * laneCount;
        rateKgPerSec += (co2Grams / 120) / 1000;
      });
      rateKgPerSec = Math.max(rateKgPerSec, 0.05);
      co2AccumRef.current += rateKgPerSec;
      timeSavedAccumRef.current += 0.0001;
      setTotalCO2(co2AccumRef.current);
      setTotalTimeSaved(timeSavedAccumRef.current);
    }, 1000);
    return () => clearInterval(ticker);
  }, [nodes]);

  const intersectionData = React.useMemo(() => {
    return intersections.map((intersection, idx) => {
      const node = nodes[idx] || null;
      let avgDensity = (intersection.p || 0) * 100;

      // Real data profile for Active / Hero Node (ITO Junction)
      if (intersection.nodeId === "284501" || idx === 0) {
        return {
          id: `INT-${idx + 1}`,
          name: intersection.name,
          status: intersection.status as any,
          peakHour: "9:00 AM",
          peakVolume: 92,
          savedCO2: (() => { const v = (92/100)*120; const s = 45*0.18; return (s*v*2.3*4)/1000; })(),
          timeSaved: 1.35,
          maxCongestionHrs: 38,
          clearanceWindow: "1 AM - 4 AM",
          hourlyData: [
            { hour: "6AM", density: 15 },
            { hour: "8AM", density: 65 },
            { hour: "10AM", density: 88 },
            { hour: "12PM", density: 45 },
            { hour: "2PM", density: 52 },
            { hour: "4PM", density: 70 },
            { hour: "6PM", density: 92 },
            { hour: "8PM", density: 60 },
            { hour: "10PM", density: 20 },
          ]
        };
      }

      // Dynamic Pseudo-Random Bimodal Simulation for all other dummy nodes
      const peakStr = PEAK_TIMES[idx] || "6:00 PM";
      let peakHourNum = parseInt(peakStr);
      if (peakStr.includes("PM") && peakHourNum !== 12) peakHourNum += 12;
      if (peakStr.includes("AM") && peakHourNum === 12) peakHourNum = 0;

      const secondaryPeak = (peakHourNum >= 12) ? peakHourNum - 9 : peakHourNum + 9;

      // Decouple from live scale to prevent flatlining when live is 100%
      const nodeBaseScale = 50 + (idx % 30); // 50-80% base height

      const hourlyData = [6, 8, 10, 12, 14, 16, 18, 20, 22].map(hour => {
        const dist1 = Math.abs(hour - peakHourNum);
        const dist2 = Math.abs(hour - secondaryPeak);

        // Narrower Gaussian curves (Sigma 1.5)
        const val1 = Math.exp(-0.5 * Math.pow(dist1 / 1.5, 2));
        const val2 = Math.exp(-0.5 * Math.pow(dist2 / 2.0, 2)) * 0.7;
        const noise = Math.abs(Math.sin((idx + 1) * hour)) * 0.15;

        const mult = Math.max(val1, val2) + noise + 0.10;

        let finalDensity = nodeBaseScale * mult * 1.5;
        if (finalDensity > 95) finalDensity = 95 - noise * 10;

        const label = hour === 12 ? "12PM" : hour > 12 ? `${hour - 12}PM` : `${hour}AM`;
        return { hour: label, density: Math.max(5, finalDensity) };
      });

      const peakDensity = Math.max(...hourlyData.map(h => h.density));
      const maxWait = node ? Math.max(...Object.values(node.lanes).map(l => l.wait_time)) : 0;

      return {
        id: `INT-${idx + 1}`,
        name: intersection.name,
        status: (intersection.status || "Green") as any,
        peakHour: PEAK_TIMES[idx] || "6:00 PM",
        peakVolume: Math.round(peakDensity),
        savedCO2: (() => { const v = (avgDensity/100)*120; const s = maxWait*0.18; return (s*v*2.3*Math.max(Object.keys(node?.lanes||{}).length,1))/1000; })(),
        timeSaved: maxWait > 0 ? Number((maxWait * 0.18 / 60).toFixed(2)) : 0.5,
        maxCongestionHrs: MAX_CONGESTION_MINS[idx] || 25,
        clearanceWindow: intersection.status === "Red" ? "1 AM – 4 AM" : "10 PM – 5 AM",
        hourlyData
      };
    });
  }, [nodes, intersections]);

  const [isLoading, setIsLoading] = useState(true);

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

    const timer = setTimeout(() => setIsLoading(false), 1200);

    return () => {
      observer.disconnect();
      clearTimeout(timer);
    };
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

  if (isLoading) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-slate-950 transition-colors duration-300">
        <div className="w-10 h-10 border-4 border-gray-200 dark:border-slate-800 border-t-blue-500 dark:border-t-blue-500 rounded-full animate-spin mb-4"></div>
        <p className="text-sm text-gray-500 dark:text-slate-400 font-mono uppercase tracking-widest">Loading Peak Data...</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col md:flex-row overflow-hidden bg-gray-50 dark:bg-slate-950 transition-colors duration-300 relative">
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
                  <p className="text-xs text-gray-500 dark:text-slate-500 font-mono">Delhi NCR · All {intersections.length} Monitored Nodes · Today</p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="text-right">
                  <p className="text-[10px] text-emerald-600 dark:text-emerald-400 uppercase tracking-wider font-bold">CO₂ Saved Today</p>
                  <p className="text-emerald-700 dark:text-emerald-300 font-bold font-mono">{totalCO2.toFixed(1)} <span className="text-gray-500 dark:text-slate-500 font-normal">kg</span></p>
                </div>
                <div className="w-px h-8 bg-gray-200 dark:bg-slate-800" />
                <div className="text-right">
                  <p className="text-[10px] text-sky-600 dark:text-cyan-400 uppercase tracking-wider font-bold">Time Saved</p>
                  <p className="text-sky-700 dark:text-cyan-300 font-bold font-mono">{totalTimeSaved.toFixed(1)} <span className="text-gray-500 dark:text-slate-500 font-normal">min/vehicle</span></p>
                </div>
                <div className="w-px h-8 bg-gray-200 dark:bg-slate-800" />
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
                  <YAxis tick={{ fill: isDark ? '#64748b' : '#94a3b8', fontSize: 10 }} axisLine={{ stroke: isDark ? '#1e293b' : '#e2e8f0' }} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toString()} />
                  <Tooltip content={<CustomTooltip isDark={isDark} unit="vehicles" isVolume={true} />} />
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
                {/* Bar Chart — Density % */}
                <div className="flex-1 h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={item.hourlyData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#1e293b" : "#e2e8f0"} vertical={false} />
                      <XAxis dataKey="hour" tick={{ fill: isDark ? '#475569' : '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: isDark ? '#475569' : '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v}%`} />
                      <Tooltip content={<CustomTooltip isDark={isDark} />} />
                      <Bar dataKey="density" radius={[2, 2, 0, 0]}>
                        {item.hourlyData.map((entry, index) => {
                          let barFill = getBarColor(item.status);
                          if (entry.density > 80) barFill = isDark ? "#ef4444" : "#dc2626"; // Red for heavy traffic
                          else if (entry.density > 55) barFill = isDark ? "#f59e0b" : "#d97706"; // Amber for moderate
                          return <Cell key={`cell-${index}`} fill={barFill} />;
                        })}
                      </Bar>
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
                    <p className="text-lg font-bold text-gray-900 dark:text-white font-mono">{item.maxCongestionHrs} <span className="text-xs text-gray-500 dark:text-slate-500 font-normal">min</span></p>
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
                      CO₂ Emission Saved
                    </div>
                    <p className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">{item.savedCO2.toFixed(2)} <span className="text-xs text-gray-500 dark:text-slate-500 font-normal">kg/day</span></p>
                  </div>
                  <div className="bg-gray-50 dark:bg-slate-800/50 rounded-lg p-3 border border-gray-100 dark:border-slate-700/30 transition-colors">
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-slate-500 uppercase tracking-wider mb-1">
                      <Clock className="w-3 h-3" />
                      Time Saved / Vehicle
                    </div>
                    <p className="text-lg font-bold font-mono text-sky-600 dark:text-cyan-400">{item.timeSaved.toFixed(2)} <span className="text-xs text-gray-500 dark:text-slate-500 font-normal">min</span></p>
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
                <p className="text-[10px] text-gray-500 dark:text-slate-600 font-mono">CO₂: {item.savedCO2.toFixed(2)} kg · Time: {item.timeSaved.toFixed(1)} min/veh</p>
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
