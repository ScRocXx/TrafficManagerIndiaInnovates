"use client";
import React, { useState } from "react";
import { Search, Bell, UserCircle, AlertCircle, Camera, Navigation, Clock, LogOut, Settings, BarChart3, Shield } from "lucide-react";
import { vulnerabilitiesData } from '../app/page';

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

export function SearchBar({ onSelect }: { onSelect?: (name: string) => void }) {
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
    <div className="absolute top-6 left-1/2 -translate-x-1/2 z-[1000] w-[400px]">
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
  const [openMenu, setOpenMenu] = useState<"notifications" | "profile" | null>(null);

  const toggleMenu = (menu: "notifications" | "profile") => {
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
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full border-2 border-white dark:border-slate-800"></span>
          </div>
        </button>

        {openMenu === "notifications" && (
          <div className="absolute right-0 top-full mt-3 w-[400px] bg-white dark:bg-slate-800 rounded-3xl shadow-2xl border border-gray-100 dark:border-slate-700/50 overflow-hidden flex flex-col max-h-[500px]">
            <div className="p-4 border-b border-gray-100 dark:border-slate-700 flex justify-between items-center bg-gray-50/50 dark:bg-slate-800/80">
              <h3 className="font-bold text-gray-800 dark:text-white">Active Alerts</h3>
              <span className="bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400 text-xs font-bold px-2 py-1 rounded-full">{vulnerabilitiesData.length} New</span>
            </div>
            <div className="overflow-y-auto w-full">
              {vulnerabilitiesData.map((notif: { id: string, status: string, type: string, last_ping: string, issue: string, location: string }) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif.id)}
                  className="p-4 border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors flex items-start space-x-3"
                >
                  <div className={`mt-0.5 p-2 rounded-full ${notif.status === 'Critical' ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' : 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'}`}>
                    <AlertCircle className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-semibold text-gray-800 dark:text-white text-sm">{notif.type} • {notif.id}</span>
                      <span className="text-xs text-gray-400 flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {new Date(notif.last_ping).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className={`text-sm mb-1 font-medium ${notif.status === 'Critical' ? 'text-red-600 dark:text-red-400' : 'text-yellow-600 dark:text-yellow-500'}`}>{notif.issue}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{notif.location}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-3 bg-gray-50 dark:bg-slate-800/80 border-t border-gray-100 dark:border-slate-700 text-center text-sm font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 cursor-pointer">
              View all hardware vulnerabilities
            </div>
          </div>
        )}
      </div>

      {/* Profile */}
      <div className="relative">
        <button
          onClick={() => toggleMenu("profile")}
          className={`w-12 h-12 rounded-full shadow-sm flex items-center justify-center hover:shadow-md transition-all ${openMenu === "profile" ? "bg-blue-50 dark:bg-blue-900/30 ring-2 ring-blue-500" : "bg-white dark:bg-slate-800"}`}
        >
          <UserCircle className={`w-7 h-7 ${openMenu === "profile" ? "text-blue-600 dark:text-blue-400" : "text-gray-600 dark:text-gray-300"}`} />
        </button>

        {openMenu === "profile" && (
          <div className="absolute right-0 top-full mt-3 w-[260px] bg-white dark:bg-slate-800 rounded-3xl shadow-2xl border border-gray-100 dark:border-slate-700/50 overflow-hidden flex flex-col">
            <div className="p-5 border-b border-gray-100 dark:border-slate-700 text-center bg-gray-50/50 dark:bg-slate-800/80">
              <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-full mx-auto flex items-center justify-center mb-3">
                <UserCircle className="w-10 h-10" />
              </div>
              <h3 className="font-bold text-gray-800 dark:text-white text-lg">Admin User</h3>
              <span className="text-xs text-gray-500 dark:text-gray-400">Delhi Traffic Authority</span>
            </div>
            <div className="p-2">
              <div className="hover:bg-gray-50 dark:hover:bg-slate-700/50 p-3 rounded-2xl cursor-pointer flex items-center text-gray-700 dark:text-gray-300 transition-colors">
                <BarChart3 className="w-5 h-5 mr-3 text-gray-400" />
                <span className="font-medium text-sm">Dashboard Analytics</span>
              </div>
              <div className="hover:bg-gray-50 dark:hover:bg-slate-700/50 p-3 rounded-2xl cursor-pointer flex items-center text-gray-700 dark:text-gray-300 transition-colors">
                <Shield className="w-5 h-5 mr-3 text-gray-400" />
                <span className="font-medium text-sm">Emergency Protocols</span>
              </div>
              <div className="hover:bg-gray-50 dark:hover:bg-slate-700/50 p-3 rounded-2xl cursor-pointer flex items-center text-gray-700 dark:text-gray-300 transition-colors">
                <Settings className="w-5 h-5 mr-3 text-gray-400" />
                <span className="font-medium text-sm">System Settings</span>
              </div>
            </div>
            <div className="p-2 border-t border-gray-100 dark:border-slate-700">
              <div className="hover:bg-red-50 dark:hover:bg-red-900/20 p-3 rounded-2xl cursor-pointer flex items-center text-red-600 dark:text-red-400 transition-colors">
                <LogOut className="w-5 h-5 mr-3" />
                <span className="font-medium text-sm">Log out securely</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
