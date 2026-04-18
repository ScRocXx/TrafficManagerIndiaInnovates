"use client";
import React, { useState, useEffect } from "react";
import { Clock, BarChart2, Cpu, Moon, Plus, Phone, Map, X } from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    setIsDarkMode(document.documentElement.classList.contains('dark'));
  }, []);
  const [contacts, setContacts] = useState(['+91 112-234-5678', '+91 987-654-3210']);

  const toggleDarkMode = () => {
    const nextMode = !isDarkMode;
    setIsDarkMode(nextMode);
    if (nextMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  const handleAddContact = () => {
    const newContact = window.prompt("Enter new emergency contact number:");
    if (newContact) {
      setContacts([...contacts, newContact]);
    }
  };

  const handleDeleteContact = (indexToRemove: number) => {
    setContacts(contacts.filter((_, index) => index !== indexToRemove));
  };

  return (
    <div className="w-[300px] h-full bg-[#f8f9fa] dark:bg-slate-900 flex flex-col p-6 border-r border-gray-200 dark:border-slate-800 transition-colors">
      <h1 className="text-2xl font-bold mb-8 text-gray-800 dark:text-white">Traffic Dashboard</h1>

      <div className="flex-1 space-y-4">
        {[
          { name: "Delhi Map", icon: Map },
          { name: "Peak hours", icon: Clock },
          { name: "Most busiest", icon: BarChart2 },
          { name: "Hardware vulnerability", icon: Cpu }
        ].map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.name;
          return (
            <button
              key={item.name}
              onClick={() => setActiveTab(item.name)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-full font-medium transition-all ${isActive
                  ? "bg-white dark:bg-slate-800 shadow-sm text-gray-800 dark:text-white hover:shadow-md"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800/50"
                }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? "text-blue-500" : ""}`} />
              <span>{item.name}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-auto space-y-6 pt-6 border-t border-gray-200 dark:border-slate-800 transition-colors">
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center space-x-3 text-gray-600 dark:text-gray-400 font-medium">
            <Moon className="w-5 h-5" />
            <span>Dark mode</span>
          </div>
          <div
            onClick={toggleDarkMode}
            className={`w-11 h-6 rounded-full relative cursor-pointer transition-colors ${isDarkMode ? 'bg-blue-500' : 'bg-gray-300 dark:bg-slate-700'}`}
          >
            <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${isDarkMode ? 'translate-x-6' : 'translate-x-1'}`}></div>
          </div>
        </div>

        <div className="px-2">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-600 dark:text-gray-400 font-medium text-sm">Emergency contacts</span>
            <button onClick={handleAddContact} className="w-6 h-6 rounded-full bg-gray-200 dark:bg-slate-700 flex items-center justify-center hover:bg-gray-300 dark:hover:bg-slate-600 transition-colors">
              <Plus className="w-4 h-4 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
          <div className="space-y-3">
            {contacts.map((contact, i) => (
              <div key={i} className="group flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                <a href={`tel:${contact}`} className="flex items-center space-x-3 hover:text-blue-500 transition-colors">
                  <Phone className="w-4 h-4" />
                  <span>{contact}</span>
                </a>
                <button
                  onClick={() => handleDeleteContact(i)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 text-red-400 hover:text-red-500 transition-all"
                  title="Delete contact"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
