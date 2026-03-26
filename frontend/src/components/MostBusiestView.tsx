"use client";
import React from "react";
import { BarChart2, ArrowUpRight, ArrowDownRight, Car, Timer, Flame } from "lucide-react";
import Link from "next/link";
import { intersections } from "@/lib/intersections";
import { ProfileAlerts } from "./Overlays";

const busiestIntersections = [
  { rank: 1, name: "ITO Junction", avgVehicles: 9800, peakVehicles: 14200, peakTime: "6:15 PM", avgWait: "14 min", trend: "up", change: "+8%", status: "Red" },
  { rank: 2, name: "Ashram Chowk", avgVehicles: 9200, peakVehicles: 13500, peakTime: "5:45 PM", avgWait: "12 min", trend: "up", change: "+5%", status: "Red" },
  { rank: 3, name: "AIIMS", avgVehicles: 8900, peakVehicles: 12800, peakTime: "6:30 PM", avgWait: "11 min", trend: "down", change: "-2%", status: "Red" },
  { rank: 4, name: "Raja Garden", avgVehicles: 8100, peakVehicles: 11900, peakTime: "5:30 PM", avgWait: "9 min", trend: "up", change: "+12%", status: "Red" },
  { rank: 5, name: "South Ext", avgVehicles: 7600, peakVehicles: 10500, peakTime: "6:00 PM", avgWait: "8 min", trend: "down", change: "-1%", status: "Red" },
  { rank: 6, name: "Connaught Place", avgVehicles: 6800, peakVehicles: 9100, peakTime: "1:00 PM", avgWait: "7 min", trend: "up", change: "+3%", status: "Yellow" },
  { rank: 7, name: "Kashmere Gate", avgVehicles: 6200, peakVehicles: 8700, peakTime: "9:00 AM", avgWait: "6 min", trend: "down", change: "-4%", status: "Yellow" },
  { rank: 8, name: "Karol Bagh", avgVehicles: 5500, peakVehicles: 7200, peakTime: "7:00 PM", avgWait: "5 min", trend: "up", change: "+1%", status: "Yellow" },
  { rank: 9, name: "Laxmi Nagar", avgVehicles: 4200, peakVehicles: 5800, peakTime: "8:30 AM", avgWait: "3 min", trend: "down", change: "-6%", status: "Green" },
  { rank: 10, name: "Dhaula Kuan", avgVehicles: 3800, peakVehicles: 5200, peakTime: "5:00 PM", avgWait: "3 min", trend: "down", change: "-3%", status: "Green" },
  { rank: 11, name: "Moolchand", avgVehicles: 3200, peakVehicles: 4100, peakTime: "6:45 PM", avgWait: "2 min", trend: "down", change: "-7%", status: "Green" },
  { rank: 12, name: "Akshardham", avgVehicles: 2800, peakVehicles: 3600, peakTime: "9:15 AM", avgWait: "1 min", trend: "down", change: "-5%", status: "Green" },
];

const statusDot: Record<string, string> = {
  Red: "bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.8)] dark:bg-red-500 dark:shadow-[0_0_8px_rgba(239,68,68,0.8)]",
  Yellow: "bg-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.8)]",
  Green: "bg-gray-400 shadow-[0_0_8px_rgba(156,163,175,0.8)] dark:bg-green-500 dark:shadow-[0_0_8px_rgba(34,197,94,0.8)]",
};

export default function MostBusiestView({ setActiveTab }: { setActiveTab?: (tab: string) => void }) {
  const sorted = [...busiestIntersections].sort((a, b) => b.avgVehicles - a.avgVehicles);

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
              <p className="text-sm text-gray-500 dark:text-gray-400">Ranked by traffic volume across Delhi NCR</p>
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
                  <span className={`w-3 h-3 rounded-full transition-colors ${statusDot[item.status]}`} />
                </div>
                <Flame className={`w-5 h-5 transition-colors ${idx === 0 ? 'text-sky-500 dark:text-red-500' : 'text-orange-400'}`} />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1 transition-colors">{item.name}</h3>
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div>
                  <p className="text-xs text-gray-400">Avg Vehicles/hr</p>
                  <p className="text-xl font-bold text-gray-800 dark:text-white transition-colors">{item.avgVehicles.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Peak</p>
                  <p className="text-xl font-bold text-sky-500 dark:text-red-500 transition-colors">{item.peakVehicles.toLocaleString()}</p>
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
                  <th className="px-6 py-3">Avg Vehicles/hr</th>
                  <th className="px-6 py-3">Peak</th>
                  <th className="px-6 py-3">Peak Time</th>
                  <th className="px-6 py-3">Avg Wait</th>
                  <th className="px-6 py-3">details</th>
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
                        <span className={`w-2.5 h-2.5 rounded-full transition-colors ${statusDot[item.status]}`} />
                        <span className="font-medium text-gray-800 dark:text-white transition-colors">{item.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-semibold text-gray-700 dark:text-gray-300 transition-colors">{item.avgVehicles.toLocaleString()}</td>
                    <td className="px-6 py-4 font-semibold text-sky-500 dark:text-red-500 transition-colors">{item.peakVehicles.toLocaleString()}</td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1 transition-colors"><Timer className="w-3.5 h-3.5" />{item.peakTime}</td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 transition-colors">{item.avgWait}</td>
                    <td className="px-6 py-4">
                      {(() => {
                        const match = intersections.find(i => i.name === item.name);
                        return match ? (
                          <Link href={`/intersection/${match.nodeId}`} className="text-sm font-medium text-sky-500 dark:text-sky-400 hover:underline cursor-pointer transition-colors">
                            View
                          </Link>
                        ) : (
                          <span className="text-sm font-medium text-gray-400 dark:text-gray-500">N/A</span>
                        );
                      })()}
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
