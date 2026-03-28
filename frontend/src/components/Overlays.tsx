"use client";
import React, { useState } from "react";
import { Search, Bell, AlertCircle, Camera, Navigation, Clock, LogOut, Settings, BarChart3, Shield } from "lucide-react";
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

const mockIntersections = [
  'ITO Junction',
  'AIIMS Intersection',
  'Connaught Place',
  'South Ext',
  'Rajiv Chowk',
  'Karol Bagh',
  'Lajpat Nagar',
  'Dwarka',
  'Rohini',
  'Vasant Kunj',
  'Saket',
  'Nehru Place',
  'Hauz Khas',
  'Chandni Chowk',
  'Dhaula Kuan',
  'Kashmere Gate',
  'Laxmi Nagar',
  'Pitampura',
  'Janakpuri',
  'Okhla',
  'Vasant Vihar',
  'Greater Kailash'
];

export function SearchBar({ onSelect, className = "absolute top-6 left-1/2 -translate-x-1/2 z-[1000] w-[400px]" }: { onSelect?: (name: string) => void, className?: string }) {
  const [isFocused, setIsFocused] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const normalizedSearchTerm = searchTerm.toLowerCase()
    .replace(/rajeev/g, 'rajiv')
    .replace(/chawk/g, 'chowk');

  const filtered = mockIntersections.filter(i => i.toLowerCase().includes(normalizedSearchTerm));

  const handleSelect = (name: string) => {
    setSearchTerm("");
    setIsFocused(false);
    if (onSelect) onSelect(name);
  };

  return (
    <div className={className}>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="block w-full pl-11 pr-4 py-3 rounded-full bg-white dark:bg-slate-800 border-0 shadow-sm focus:ring-2 focus:ring-blue-500 outline-none transition-shadow text-gray-800 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
          placeholder="Search intersections..."
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
        />
        {isFocused && searchTerm && filtered.length > 0 && (
          <div className="absolute top-full mt-2 w-full bg-white dark:bg-slate-800 rounded-2xl shadow-lg border border-gray-100 dark:border-slate-700 overflow-hidden">
            <ul className="py-2">
              {filtered.map(item => (
                <li
                  key={item}
                  onMouseDown={() => handleSelect(item)}
                  className="px-4 py-2 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer text-gray-700 dark:text-gray-300 flex items-center space-x-2"
                >
                  <Search className="w-4 h-4 text-gray-400" /> <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export function ProfileAlerts({ setActiveTab, className = "absolute top-6 right-6" }: { setActiveTab?: (tab: string) => void; className?: string }) {
  const [openMenu, setOpenMenu] = useState<"notifications" | null>(null);
  const { vulnerabilities: vulnerabilitiesData } = useNetworkStatus();

  const toggleMenu = (menu: "notifications") => {
    if (openMenu === menu) setOpenMenu(null);
    else setOpenMenu(menu);
  };

  const handleNotificationClick = (id: string) => {
    if (setActiveTab) {
      setActiveTab("Hardware vulnerability");
      setOpenMenu(null);
      setTimeout(() => {
        const el = document.getElementById(`vuln-${id}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.classList.add('ring-4', 'ring-blue-500', 'transition-all');
          setTimeout(() => el.classList.remove('ring-4', 'ring-blue-500'), 2000);
        }
      }, 300);
    }
  };

  return (
    <div className={`${className} z-[1000] flex space-x-3`}>
      {/* Notifications */}
      <div className="relative">
        <button
          onClick={() => toggleMenu("notifications")}
          className={`w-12 h-12 rounded-full shadow-sm flex items-center justify-center hover:shadow-md transition-all ${openMenu === "notifications" ? "bg-blue-50 dark:bg-blue-900/30 ring-2 ring-blue-500" : "bg-white dark:bg-slate-800"}`}
        >
          <div className="relative">
            <Bell className={`w-6 h-6 ${openMenu === "notifications" ? "text-blue-600 dark:text-blue-400" : "text-gray-600 dark:text-gray-300"}`} />
            {vulnerabilitiesData.length > 0 && (
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full border-2 border-white dark:border-slate-800"></span>
            )}
          </div>
        </button>
      </div>
    </div>
  );
}
