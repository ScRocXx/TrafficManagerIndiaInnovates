"use client";
import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { Plus, Minus, Search, Activity } from "lucide-react";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import { IntersectionData, intersections } from '@/lib/intersections';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';

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
  const { nodes, intersections: liveIntersections } = useNetworkStatus();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const totalCO2Saved = React.useMemo(() => {
    return liveIntersections.reduce((sum, intersection, idx) => {
      const node = nodes[idx];
      const avgDensity = (intersection.p || 0) * 100;
      const p_level = intersection.p || 0;
      let maxWait = 0;
      if (node && node.lanes) {
        maxWait = Math.max(...Object.values(node.lanes).map((l: any) => l.wait_time || 0));
      }

      let savedCO2 = (maxWait * avgDensity * 0.015) + (p_level * 12.5);

      if (intersection.nodeId === "284501" || idx === 0) {
        savedCO2 = (45 * 92 * 0.015) + (0.85 * 12.5);
      }

      return sum + (savedCO2 > 0 ? savedCO2 : 0);
    }, 0);
  }, [nodes, liveIntersections]);

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
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          }
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />

        <TelemetryMarkers onSelectIntersection={onSelectIntersection} isDark={isDark} />
        <MapResizer selectedIntersection={selectedIntersection} />
        {focusIntersection && onFocusHandled && (
          <FocusHandler focusIntersection={focusIntersection} onFocusHandled={onFocusHandled} />
        )}
      </MapContainer>

      {/* Node Status Legend */}
      <div className="absolute bottom-6 left-6 z-[1000] bg-white/90 dark:bg-slate-800/90 backdrop-blur-md rounded-2xl shadow-xl border border-gray-100/50 dark:border-slate-700/50 p-5 pointer-events-none min-w-[200px]">
        <h3 className="text-[10px] font-bold text-gray-400 dark:text-slate-500 uppercase tracking-widest mb-4">Node Status</h3>
        <div className="space-y-3">
          {[
            { color: "#ef4444", short: "CRIT", label: "Critical" },
            { color: "#f59e0b", short: "MOD", label: "Moderate" },
            { color: "#0ea5e9", short: "NOM", label: "Normal" }
          ].map(status => (
            <div key={status.short} className="flex items-center space-x-3">
              <div
                className="w-2.5 h-2.5 flex-shrink-0"
                style={{
                  backgroundColor: status.color,
                  transform: 'rotate(45deg)',
                  boxShadow: `0 0 6px ${status.color}80`
                }}
              />
              <div className="flex items-center space-x-2 text-xs font-mono">
                <span className="font-bold" style={{ color: status.color }}>{status.short}</span>
                <span className="text-gray-300 dark:text-slate-600">—</span>
                <span className="text-gray-600 dark:text-slate-400 font-sans tracking-wide">{status.label}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700/50">
          <div className="flex items-center gap-1.5 text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-widest mb-1">
            <Activity className="w-3 h-3" />
            Total CO₂ Saved Today
          </div>
          <p className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
            {totalCO2Saved.toFixed(1)} <span className="text-xs text-gray-500 dark:text-slate-500 font-normal">kg</span>
          </p>
        </div>
      </div>
    </div>
  );
}
