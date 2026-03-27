"use client";
import React, { useState } from "react";
import { BarChart2, ArrowUpRight, ArrowDownRight, Car, Timer, Flame } from "lucide-react";
import Link from "next/link";
import { ProfileAlerts } from "./Overlays";
import { useNetworkStatus, PEAK_TIMES } from "@/hooks/useNetworkStatus";

const statusDot: Record<string, string> = {
  Red: "bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.8)] dark:bg-red-500 dark:shadow-[0_0_8px_rgba(239,68,68,0.8)]",
  Yellow: "bg-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.8)]",
  Green: "bg-gray-400 shadow-[0_0_8px_rgba(156,163,175,0.8)] dark:bg-green-500 dark:shadow-[0_0_8px_rgba(34,197,94,0.8)]",
};

export default function MostBusiestView({ setActiveTab }: { setActiveTab?: (tab: string) => void }) {
  const { nodes, intersections } = useNetworkStatus();

  // Build dynamic rankings from live data
  const sorted = React.useMemo(() => {
    return intersections.map((inter, idx) => {
      const node = nodes[idx] || null;
      const lanes = node ? Object.values(node.lanes) : [];
      const avgDensity = lanes.length ? Math.round(lanes.reduce((s, l) => s + l.density, 0) / lanes.length) : 0;
      const peakDensity = lanes.length ? Math.round(Math.max(...lanes.map(l => l.density))) : 0;
      const maxWait = lanes.length ? Math.max(...lanes.map(l => l.wait_time)) : 0;
      const avgWaitStr = maxWait >= 60 ? `${Math.round(maxWait / 60)} min` : `${maxWait}s`;

      return {
        rank: 0,
        name: inter.name,
        avgDensity,
        peakDensity,
        peakTime: PEAK_TIMES[idx] || "6:00 PM",
        avgWait: avgWaitStr,
        trend: avgDensity > 50 ? "up" as const : "down" as const,
        change: avgDensity > 50 ? `+${Math.round(avgDensity * 0.08)}%` : `-${Math.round((100 - avgDensity) * 0.05)}%`,
        status: inter.status,
        id: inter.id,
      };
    })
    .sort((a, b) => b.avgDensity - a.avgDensity)
    .map((item, idx) => ({ ...item, rank: idx + 1 }));
  }, [nodes, intersections]);

  const [isLoading, setIsLoading] = useState(true);

  React.useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1200);
    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-slate-950 transition-colors duration-300">
        <div className="w-10 h-10 border-4 border-gray-200 dark:border-slate-800 border-t-orange-500 dark:border-t-orange-500 rounded-full animate-spin mb-4"></div>
        <p className="text-sm text-gray-500 dark:text-slate-400 font-mono uppercase tracking-widest">Loading Activity...</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-y-auto bg-gray-50 dark:bg-slate-950 p-8 transition-colors duration-300 relative">
      {/* Profile & Notification Buttons */}
      <ProfileAlerts setActiveTab={setActiveTab} />
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-orange-100 dark:bg-orange-900/40 flex items-center justify-center transition-colors">
              <BarChart2 className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Busiest Intersections</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">Ranked by live density across Delhi NCR</p>
            </div>
          </div>

        </div>

        {/* Top 3 Cards */}
        <div className="grid grid-cols-3 gap-4">
          {sorted.slice(0, 3).map((item, idx) => (
            <div key={item.name} className={`relative overflow-hidden bg-white dark:bg-slate-900 p-6 rounded-2xl border shadow-sm transition-colors ${idx === 0 ? 'border-sky-200 dark:border-red-800/50 ring-1 ring-sky-100 dark:ring-red-900/30' : 'border-gray-100 dark:border-slate-800'}`}>
              {idx === 0 && <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-sky-500 to-sky-400 dark:from-red-500 dark:to-orange-500" />}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${idx === 0 ? 'bg-sky-500 dark:bg-red-500 text-white' : idx === 1 ? 'bg-orange-500 text-white' : 'bg-yellow-400 text-gray-900'}`}>#{item.rank}</span>
                  <span className={`w-3 h-3 rounded-full transition-colors ${statusDot[item.status || "Green"]}`} />
                </div>
                <Flame className={`w-5 h-5 transition-colors ${idx === 0 ? 'text-sky-500 dark:text-red-500' : 'text-orange-400'}`} />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1 transition-colors">{item.name}</h3>
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div>
                  <p className="text-xs text-gray-400">Avg Density</p>
                  <p className="text-xl font-bold text-gray-800 dark:text-white transition-colors">{item.avgDensity}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Peak</p>
                  <p className="text-xl font-bold text-sky-500 dark:text-red-500 transition-colors">{item.peakDensity}%</p>
                </div>
              </div>
              <div className="flex items-center gap-1 mt-3">
                {item.trend === "up" ? <ArrowUpRight className="w-4 h-4 text-sky-500 dark:text-red-500" /> : <ArrowDownRight className="w-4 h-4 text-emerald-500" />}
                <span className={`text-sm font-medium transition-colors ${item.trend === "up" ? "text-sky-500 dark:text-red-500" : "text-emerald-500"}`}>{item.change}</span>
                <span className="text-xs text-gray-400 ml-1">vs last week</span>
              </div>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-slate-800 shadow-sm overflow-hidden transition-colors">
          <div className="p-6 border-b border-gray-100 dark:border-slate-800 transition-colors">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white transition-colors">All Intersections</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-100 dark:border-slate-800 transition-colors">
                  <th className="px-6 py-3">Rank</th>
                  <th className="px-6 py-3">Intersection</th>
                  <th className="px-6 py-3">Avg Density</th>
                  <th className="px-6 py-3">Peak Density</th>
                  <th className="px-6 py-3">Peak Time</th>
                  <th className="px-6 py-3">Avg Wait</th>
                  <th className="px-6 py-3">Details</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((item) => (
                  <tr key={item.name} className="border-b border-gray-50 dark:border-slate-800/50 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4">
                      <span className="w-7 h-7 rounded-full bg-gray-100 dark:bg-slate-800 flex items-center justify-center text-sm font-bold text-gray-600 dark:text-gray-300 transition-colors">{item.rank}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full transition-colors ${statusDot[item.status || "Green"]}`} />
                        <span className="font-medium text-gray-800 dark:text-white transition-colors">{item.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-semibold text-gray-700 dark:text-gray-300 transition-colors">{item.avgDensity}%</td>
                    <td className="px-6 py-4 font-semibold text-sky-500 dark:text-red-500 transition-colors">{item.peakDensity}%</td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1 transition-colors"><Timer className="w-3.5 h-3.5" />{item.peakTime}</td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 transition-colors">{item.avgWait}</td>
                    <td className="px-6 py-4">
                      <Link href={`/intersection/${item.id}`} className="text-sm font-medium text-sky-500 dark:text-sky-400 hover:underline cursor-pointer transition-colors">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
