"use client";
import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { Plus, Minus } from "lucide-react";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import { IntersectionData, intersections } from '@/lib/intersections';

const STATUS_COLORS: Record<string, { hex: string; label: string }> = {
  Red: { hex: "#ef4444", label: "CRIT" },
  Yellow: { hex: "#f59e0b", label: "MOD" },
  Green: { hex: "#12aa1eff", label: "NOM" },
};

function createTelemetryIcon(item: IntersectionData) {
  const { hex } = STATUS_COLORS[item.status] || STATUS_COLORS.Green;
  const shortName = item.name.length > 10 ? item.name.substring(0, 9) + "…" : item.name;

  const html = `
    <div style="display:flex;align-items:center;gap:0;pointer-events:auto;position:relative;">
      <div style="width:7px;height:7px;background:${hex};transform:rotate(45deg);border:1px solid rgba(0,0,0,0.15);box-shadow:0 0 4px ${hex}50;flex-shrink:0;z-index:2;"></div>
      <div style="width:12px;height:1px;background:${hex}70;flex-shrink:0;"></div>
      <div style="background:rgba(15,23,42,0.82);border:1px solid ${hex}40;border-radius:2px;padding:1px 5px;white-space:nowrap;font-family:ui-monospace,'Cascadia Code',monospace;font-size:9px;line-height:13px;color:#cbd5e1;letter-spacing:0.01em;backdrop-filter:blur(3px);">
        <span style="color:${hex};font-weight:700;">${shortName}</span>
        <span style="color:#475569;margin:0 2px;">│</span>
        <span style="color:#94a3b8;font-size:8px;">ID:</span>
        <span style="color:#e2e8f0;font-weight:500;font-size:8px;">${item.nodeId}</span>
      </div>
    </div>
  `;

  return L.divIcon({
    className: "!bg-transparent !border-0 telemetry-node",
    html,
    iconSize: [145, 16],
    iconAnchor: [4, 8],
    popupAnchor: [70, -8],
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
      const currentStatus = live?.status || item.status;
      const currentP = live ? live.congestionLevel : item.p;
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
    <div className="absolute bottom-8 right-6 z-[1000] flex flex-col shadow-md rounded-lg overflow-hidden bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm border border-gray-200 dark:border-slate-700/50 transition-colors">
      <button
        onClick={() => map.zoomIn()}
        className="w-10 h-10 flex items-center justify-center hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors border-b border-gray-200 dark:border-slate-700/50 text-gray-600 dark:text-slate-400"
        title="Zoom In"
      >
        <Plus className="w-4 h-4" />
      </button>
      <button
        onClick={() => map.zoomOut()}
        className="w-10 h-10 flex items-center justify-center hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors text-gray-600 dark:text-slate-400"
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
            ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          }
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />

        <TelemetryMarkers onSelectIntersection={onSelectIntersection} isDark={isDark} />
        <CustomZoomControl />
        <MapResizer selectedIntersection={selectedIntersection} />
        {focusIntersection && onFocusHandled && (
          <FocusHandler focusIntersection={focusIntersection} onFocusHandled={onFocusHandled} />
        )}
      </MapContainer>

      {/* Map Legend */}
      <div className="absolute bottom-8 left-6 z-[1000] bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm border border-gray-200 dark:border-slate-700/50 rounded-lg px-4 py-3 shadow-sm transition-colors">
        <p className="text-[9px] text-gray-400 dark:text-slate-500 uppercase tracking-widest font-semibold mb-2">Node Status</p>
        <div className="flex flex-col gap-1.5">
          {Object.entries(STATUS_COLORS).map(([key, { hex, label }]) => (
            <div key={key} className="flex items-center gap-2">
              <div style={{ width: 5, height: 5, background: hex, transform: "rotate(45deg)" }} />
              <span className="text-[9px] font-mono text-gray-500 dark:text-slate-400">{label}</span>
              <span className="text-[9px] text-gray-400 dark:text-slate-500">— {key === "Red" ? "Critical" : key === "Yellow" ? "Moderate" : "Normal"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
