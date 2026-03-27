"use client";
import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { Plus, Minus, Search } from "lucide-react";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import { IntersectionData, intersections } from '@/lib/intersections';

const STATUS_COLORS: Record<string, { hex: string; label: string }> = {
  Red: { hex: "#ef4444", label: "CRIT" },
  Yellow: { hex: "#f59e0b", label: "MOD" },
  Green: { hex: "#0ea5e9", label: "NOM" },
};

function createTelemetryIcon(item: IntersectionData & { status: string; p: number }) {
  const { hex, label } = STATUS_COLORS[item.status] || STATUS_COLORS.Green;
  const shortName = item.name.length > 12 ? item.name.substring(0, 11) + "…" : item.name;

  const html = `
    <div style="display:flex;align-items:center;gap:0;pointer-events:auto;position:relative;filter: drop-shadow(0 0 2px rgba(0,0,0,0.5));">
      <!-- Diamond Marker -->
      <div style="width:8px;height:8px;background:${hex};transform:rotate(45deg);border:1.5px solid rgba(255,255,255,0.2);box-shadow:0 0 6px ${hex}80;flex-shrink:0;z-index:2;"></div>
      
      <!-- Connection Line -->
      <div style="width:14px;height:1px;background:linear-gradient(to right, ${hex}, ${hex}40);flex-shrink:0;margin:0 -1px;"></div>
      
      <!-- Tech Label -->
      <div style="background:rgba(15,23,42,0.92);border:1px solid ${hex}60;border-left:2.5px solid ${hex};border-radius:2px;padding:2px 8px;white-space:nowrap;font-family:ui-monospace,'Cascadia Code',monospace;font-size:10px;line-height:14px;color:#f8fafc;letter-spacing:0.02em;backdrop-filter:blur(4px);display:flex;align-items:center;gap:6px;box-shadow: 4px 4px 10px rgba(0,0,0,0.3);">
        <span style="color:${hex};font-weight:800;text-transform:uppercase;">${shortName}</span>
        <span style="color:rgba(255,255,255,0.15);font-size:8px;">│</span>
        <span style="color:#64748b;font-size:9px;font-weight:600;">ID:</span>
        <span style="color:#94a3b8;font-weight:500;font-size:9px;">${item.nodeId}</span>
      </div>
    </div>
  `;

  return L.divIcon({
    className: "!bg-transparent !border-0 telemetry-node",
    html,
    iconSize: [160, 20],
    iconAnchor: [4, 10],
    popupAnchor: [80, -10],
  });
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function TelemetryMarkers({ onSelectIntersection, isDark }: { onSelectIntersection: (i: IntersectionData) => void, isDark: boolean }) {
  const map = useMap();
  const onSelectRef = React.useRef(onSelectIntersection);
  const [liveStatus, setLiveStatus] = useState<Record<string, { status: string; congestionLevel: number }>>({});

  useEffect(() => {
    onSelectRef.current = onSelectIntersection;
  }, [onSelectIntersection]);

  // Poll live traffic data for map marker status colors
  useEffect(() => {
    const fetchLive = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://india-innovate-backend.onrender.com";
        const res = await fetch(`${API_URL}/api/traffic`);
        if (!res.ok) return;
        const data: any[] = await res.json();
        const statusMap: Record<string, { status: string; congestionLevel: number }> = {};
        data.forEach((d: any) => {
          statusMap[d.nodeId] = { status: d.status || "Green", congestionLevel: d.congestionLevel || 0 };
        });
        setLiveStatus(statusMap);
      } catch (e) {
        // Silently fallback to static data
      }
    };
    fetchLive();
    const interval = setInterval(fetchLive, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const markers: L.Marker[] = [];

    intersections.forEach((item) => {
      // Merge live status if available
      const live = liveStatus[item.nodeId];
      
      let currentStatus: string;
      let currentP: number;

      if (live) {
        currentStatus = live.status || "Green";
        currentP = live.congestionLevel;
      } else {
        // Deterministic mock randomization
        const seed = parseInt(item.nodeId.slice(-3)) || 100;
        currentStatus = (seed % 10 < 2) ? "Red" : (seed % 10 < 5) ? "Yellow" : "Green";
        
        // Scale P-value based on mock status
        if (currentStatus === "Red") {
          currentP = 0.75 + (seed % 20) / 100;
        } else if (currentStatus === "Yellow") {
          currentP = 0.45 + (seed % 15) / 100;
        } else {
          currentP = 0.12 + (seed % 10) / 100;
        }
      }

      const enrichedItem = { ...item, status: currentStatus, p: currentP };

      const { hex } = STATUS_COLORS[currentStatus] || STATUS_COLORS.Green;
      const statusLabel = currentStatus === "Red" ? "Critical" : currentStatus === "Yellow" ? "Moderate" : "Normal";

      const marker = L.marker([item.lat, item.lng], {
        icon: createTelemetryIcon(enrichedItem),
        interactive: true,
      });

      const popupContent = `
        <div style="text-align:center;min-width:210px;padding:6px 2px;">
          <p style="font-weight:700;font-size:14px;${isDark ? 'color:#f1f5f9' : 'color:#1e293b'};margin:0 0 2px;">${item.name}</p>
          <p style="font-family:ui-monospace,monospace;font-size:11px;${isDark ? 'color:#94a3b8' : 'color:#64748b'};margin:0 0 10px;">[${item.nodeId}]</p>
          <div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:12px;">
            <span style="width:7px;height:7px;border-radius:50%;background:${hex};display:inline-block;"></span>
            <span style="font-size:11px;${isDark ? 'color:#94a3b8' : 'color:#475569'};font-weight:500;">${statusLabel}</span>
            <span style="color:#cbd5e1;margin:0 2px;">·</span>
            <span style="font-size:11px;${isDark ? 'color:#94a3b8' : 'color:#475569'};">P-Value: <strong style="${isDark ? 'color:#f8fafc' : 'color:#1e293b'};">${currentP.toFixed(2)}</strong></span>
          </div>
          <button
            id="btn-view-${item.id}"
            style="width:100%;padding:9px 16px;background:#2563eb;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;letter-spacing:0.02em;transition:background 0.15s;"
            onmouseover="this.style.background='#1d4ed8'"
            onmouseout="this.style.background='#2563eb'"
          >
            View Command Center
          </button>
        </div>
      `;

      const popup = L.popup({
        className: isDark ? "dark-popup" : "light-popup",
        closeButton: true,
        maxWidth: 260,
        minWidth: 220,
      }).setContent(popupContent);

      marker.bindPopup(popup);

      marker.on("popupopen", () => {
        const btn = document.getElementById(`btn-view-${item.id}`);
        if (btn) {
          btn.onclick = () => {
            marker.closePopup();
            window.location.href = `/intersection/${item.nodeId}`;
          };
        }
      });

      marker.addTo(map);
      markers.push(marker);
    });

    return () => {
      markers.forEach((m) => map.removeLayer(m));
    };
  }, [map, isDark, liveStatus]);

  return null;
}

function CustomZoomControl() {
  const map = useMap();
  return (
    <div className="absolute top-24 right-6 z-[1000] flex flex-col shadow-xl rounded-lg overflow-hidden bg-slate-900/90 backdrop-blur-sm border border-slate-700/50 transition-colors">
      <button
        onClick={() => map.zoomIn()}
        className="w-10 h-10 flex items-center justify-center hover:bg-slate-700 transition-colors border-b border-slate-700 text-slate-400"
        title="Zoom In"
      >
        <Plus className="w-4 h-4" />
      </button>
      <button
        onClick={() => map.zoomOut()}
        className="w-10 h-10 flex items-center justify-center hover:bg-slate-700 transition-colors text-slate-400"
        title="Zoom Out"
      >
        <Minus className="w-4 h-4" />
      </button>
    </div>
  );
}

function MapResizer({ selectedIntersection }: { selectedIntersection: IntersectionData | null }) {
  const map = useMap();

  useEffect(() => {
    // Staggered invalidations for split-screen flex layout settling
    const timeouts = [100, 350, 750, 1500].map((t) =>
      setTimeout(() => map.invalidateSize(), t)
    );
    map.invalidateSize();
    return () => timeouts.forEach(clearTimeout);
  }, [map, selectedIntersection]);

  useEffect(() => {
    const handleResize = () => map.invalidateSize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [map]);

  return null;
}

function FocusHandler({ focusIntersection, onFocusHandled }: { focusIntersection: string | null; onFocusHandled: () => void }) {
  const map = useMap();
  const onFocusRef = React.useRef(onFocusHandled);

  useEffect(() => {
    onFocusRef.current = onFocusHandled;
  }, [onFocusHandled]);

  useEffect(() => {
    if (!focusIntersection) return;
    const searchTarget = focusIntersection.toLowerCase().replace(/\s+/g, '');
    const match = intersections.find((i) => i.name.toLowerCase().replace(/\s+/g, '').includes(searchTarget));
    if (match) map.flyTo([match.lat, match.lng], 15, { duration: 1.2 });
    onFocusRef.current();
  }, [focusIntersection, map]);
  return null;
}

interface MapProps {
  onSelectIntersection: (i: IntersectionData) => void;
  selectedIntersection: IntersectionData | null;
  focusIntersection?: string | null;
  onFocusHandled?: () => void;
}

export default function MapComponent({ onSelectIntersection, selectedIntersection, focusIntersection, onFocusHandled }: MapProps) {
  const [isDark, setIsDark] = useState(false);

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

  return (
    <div className="w-full h-full relative bg-gray-100 dark:bg-slate-950 transition-colors duration-300">
      <MapContainer
        center={[28.6139, 77.2090]}
        zoom={13}
        minZoom={10}
        maxBounds={[[28.1, 76.8], [29.0, 77.6]]}
        maxBoundsViscosity={1.0}
        zoomControl={false}
        className="w-full h-full z-0"
      >
        <TileLayer
          key={isDark ? "dark" : "light"}
          url={isDark
            ? "https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
            : "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png"
          }
          attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        <TelemetryMarkers onSelectIntersection={onSelectIntersection} isDark={isDark} />
        <CustomZoomControl />
        <MapResizer selectedIntersection={selectedIntersection} />
        {focusIntersection && onFocusHandled && (
          <FocusHandler focusIntersection={focusIntersection} onFocusHandled={onFocusHandled} />
        )}
      </MapContainer>

      {/* Floating Search Pill - Matches the visual reference */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 z-[1000] w-full max-w-lg px-4 drop-shadow-2xl">
        <div className="relative group">
          <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none">
            <Search className="w-5 h-5 text-slate-500 group-focus-within:text-sky-400 transition-colors" />
          </div>
          <input
            type="text"
            placeholder="Search intersections..."
            className="w-full h-14 pl-14 pr-24 bg-slate-900/90 backdrop-blur-xl border border-slate-700/50 rounded-2xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/30 focus:border-sky-500/40 shadow-[0_20px_50px_rgba(0,0,0,0.5)] transition-all"
            onChange={(e) => {
               // Optional: trigger flyTo on search
            }}
          />
          <div className="absolute right-5 top-1/2 -translate-y-1/2 flex items-center">
            <div className="flex flex-col items-end">
              <span className="text-[9px] font-mono text-slate-500 uppercase tracking-tighter leading-none mb-1">active_node</span>
              <span className="text-[11px] font-mono text-sky-400 font-bold leading-none">ID: 284501</span>
            </div>
          </div>
        </div>
      </div>

      {/* Redesigned Map Legend - Matches the visual reference */}
      <div className="absolute bottom-8 left-8 z-[1000] bg-slate-900/90 backdrop-blur-xl border border-slate-700/60 rounded-xl px-5 py-4 shadow-2xl transition-transform hover:scale-105 duration-300">
        <p className="text-[10px] text-slate-500 uppercase tracking-widest font-black mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-pulse"></span>
          NODE STATUSES
        </p>
        <div className="flex flex-col gap-3">
          {Object.entries(STATUS_COLORS).map(([key, { hex, label }]) => (
            <div key={key} className="flex items-center gap-4 group">
              <div style={{ width: 7, height: 7, background: hex, transform: "rotate(45deg)", boxShadow: `0 0 8px ${hex}80` }} className="transition-transform group-hover:scale-125" />
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono font-black w-10 transition-colors" style={{ color: hex }}>{label}</span>
                <span className="text-[11px] font-mono text-slate-600 tracking-tighter">—</span>
                <span className="text-[11px] font-medium text-slate-400 group-hover:text-slate-200 transition-colors">{key === "Red" ? "Critical" : key === "Yellow" ? "Moderate" : "Normal"}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
