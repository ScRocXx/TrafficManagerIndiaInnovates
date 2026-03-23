"use client";
import React, { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import {
  X, Phone, Shield, AlertTriangle,
  Video, Lock, Unlock, Siren, CheckCircle, XCircle, Power
} from "lucide-react";
import { intersections, type IntersectionData } from "@/lib/intersections";
import AmbulanceModal from "@/components/AmbulanceModal";
import { SearchBar, ProfileAlerts } from "@/components/Overlays";

const MapComponent = dynamic(
  () => import("@/components/MapComponent"),
  { ssr: false }
);

/* ── Lane mock data ── */
interface LaneData {
  direction: string;
  signal: "GREEN" | "RED";
  density: string;
  waitTime: string;
  greenTime: string;
}

const LANE_DATA: LaneData[] = [
  { direction: "North", signal: "GREEN", density: "72%", waitTime: "0s", greenTime: "45s" },
  { direction: "South", signal: "RED", density: "58%", waitTime: "32s", greenTime: "—" },
  { direction: "East", signal: "RED", density: "85%", waitTime: "48s", greenTime: "—" },
  { direction: "West", signal: "GREEN", density: "41%", waitTime: "0s", greenTime: "38s" },
];

const LOCAL_CONTACTS = [
  { name: "Traffic Police – Division HQ", phone: "+91 11-2301-5100", role: "Traffic Control" },
  { name: "Fire Station – Sector 4", phone: "+91 11-2336-7800", role: "Fire & Rescue" },
  { name: "Nearest Hospital (LNJP)", phone: "+91 11-2323-4567", role: "Medical Emergency" },
];

const ADMIN_PIN = "0000";

/* ── Camera Feed Placeholder ── */
function CameraFeed({ lane }: { lane: LaneData }) {
  const isGreen = lane.signal === "GREEN";
  return (
    <div className="flex flex-col">
      <div
        className={`relative aspect-video bg-slate-900 rounded-xl flex items-center justify-center overflow-hidden transition-shadow duration-300 ${isGreen
          ? "ring-2 ring-green-500 shadow-[0_0_15px_rgba(34,197,94,0.4)]"
          : "ring-2 ring-red-500 shadow-[0_0_15px_rgba(239,68,68,0.4)]"
          }`}
      >
        <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full animate-pulse ${isGreen ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-[10px] text-white/80 font-mono uppercase tracking-wider">{lane.direction}</span>
        </div>
        <div className="absolute top-2.5 right-2.5">
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${isGreen ? "bg-green-500/20 text-green-400 border border-green-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"
            }`}>{lane.signal}</span>
        </div>
        <Video className="w-8 h-8 text-slate-700" />
        <p className="absolute bottom-2.5 text-[10px] text-slate-500 font-mono">Feed connecting...</p>
      </div>
      <div className="grid grid-cols-3 gap-1.5 mt-2">
        {[
          { label: "Density", value: lane.density },
          { label: "Wait", value: lane.waitTime },
          { label: "Green", value: lane.greenTime },
        ].map((s) => (
          <div key={s.label} className="bg-gray-50 dark:bg-slate-800/50 rounded-lg px-2 py-1.5 border border-gray-100 dark:border-slate-700/50 text-center transition-colors">
            <p className="text-[8px] text-gray-400 dark:text-slate-500 uppercase tracking-wider font-semibold">{s.label}</p>
            <p className="text-xs font-bold text-gray-800 dark:text-slate-200">{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Emergency Compass ── */
function EmergencyCompass({ onAmbulanceClick }: { onAmbulanceClick: () => void }) {
  const dirs = ["N", "E", "S", "W"] as const;
  const ambulanceDir = "N";
  const positions: Record<string, string> = {
    N: "top-1 left-1/2 -translate-x-1/2",
    E: "right-1 top-1/2 -translate-y-1/2",
    S: "bottom-1 left-1/2 -translate-x-1/2",
    W: "left-1 top-1/2 -translate-y-1/2",
  };

  return (
    <div className="relative w-32 h-32 flex-shrink-0">
      <div className="absolute inset-0 rounded-full border-2 border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-inner transition-colors" />
      <div className="absolute inset-3 rounded-full border border-gray-100 dark:border-slate-700/50 bg-gray-50/50 dark:bg-slate-800/50 transition-colors" />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-3 h-3 rounded-full bg-gray-400 dark:bg-slate-500 border-2 border-white dark:border-slate-900 shadow transition-colors" />
      </div>
      {dirs.map((d) => {
        const isAmb = d === ambulanceDir;
        return (
          <div key={d} className={`absolute ${positions[d]} flex flex-col items-center`}>
            {isAmb ? (
              <button onClick={onAmbulanceClick} className="relative">
                <span className="absolute -inset-1 rounded-full bg-red-500/30 animate-ping" />
                <span className="relative text-xs font-bold text-red-600 bg-red-50 border border-red-200 rounded-full w-7 h-7 flex items-center justify-center shadow-sm dark:bg-red-900/30 dark:border-red-500/30 dark:text-red-400">{d}</span>
              </button>
            ) : (
              <span className="text-[10px] font-bold text-gray-400 dark:text-slate-500 w-6 h-6 flex items-center justify-center">{d}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Toast Notification ── */
interface ToastData { message: string; type: "success" | "error" }

function Toast({ toast, onDone }: { toast: ToastData; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2500);
    return () => clearTimeout(t);
  }, [onDone, toast]);

  return (
    <div className={`fixed top-6 right-6 z-[9998] flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold border transition-all animate-[slideIn_0.3s_ease-out] ${toast.type === "success"
      ? "bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800/50"
      : "bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800/50"
      }`}>
      {toast.type === "success" ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
      {toast.message}
    </div>
  );
}

/* ── Dark Console PIN Input ── */
function ConsolePinInput({ onResult }: { onResult: (ok: boolean) => void }) {
  const [pin, setPin] = useState("");
  const [shake, setShake] = useState(false);

  const submit = () => {
    if (pin === ADMIN_PIN) {
      onResult(true);
    } else {
      setShake(true);
      onResult(false);
      setTimeout(() => { setShake(false); setPin(""); }, 600);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Lock className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
      <input
        type="password"
        maxLength={4}
        value={pin}
        onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
        placeholder="PIN"
        autoFocus
        className={`w-16 text-center text-xs font-mono py-1.5 px-2 rounded-lg border outline-none transition-all placeholder-gray-400 dark:placeholder-slate-600 bg-white dark:bg-slate-800/80 text-gray-800 dark:text-slate-200 ${shake
          ? "border-red-500 animate-[shake_0.3s_ease-in-out]"
          : "border-gray-300 dark:border-slate-600 focus:border-blue-500 dark:focus:border-cyan-500 focus:ring-1 focus:ring-blue-500/30 dark:focus:ring-cyan-500/30"
          }`}
        onKeyDown={(e) => e.key === "Enter" && submit()}
      />
      <button onClick={submit} className="text-[10px] px-2.5 py-1.5 bg-blue-600 dark:bg-cyan-600 hover:bg-blue-500 dark:hover:bg-cyan-500 text-white rounded-md font-semibold transition-colors shadow-sm">
        OK
      </button>
    </div>
  );
}

/* ══════════════════════════════════════ */
/* ── Main Page ── */
/* ══════════════════════════════════════ */
export default function IntersectionPage() {
  const params = useParams();
  const router = useRouter();
  const [showAmbulanceModal, setShowAmbulanceModal] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);

  // Lane states
  const [laneStates, setLaneStates] = useState<Record<string, "RED" | "YEL" | "GRN">>({
    North: "GRN", South: "RED", East: "RED", West: "GRN",
  });

  // Timers and Overrides
  const [laneActive, setLaneActive] = useState<Record<string, boolean>>({
    North: false, South: false, East: false, West: false,
  });
  const [laneTimers, setLaneTimers] = useState<Record<string, number>>({
    North: 0, South: 0, East: 0, West: 0,
  });
  const [unlockedLanes, setUnlockedLanes] = useState<Record<string, boolean>>({
    North: false, South: false, East: false, West: false,
  });
  const [pinOpenLane, setPinOpenLane] = useState<string | null>(null);

  // Code Red
  const [codeRed, setCodeRed] = useState(false);
  const [codeRedPinOpen, setCodeRedPinOpen] = useState(false);
  const [codeRedTimer, setCodeRedTimer] = useState<number>(0);

  const id = Number(params?.id);
  const intersection = intersections.find((i) => i.id === id);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type });
  }, []);

  // Global Tick for Timers
  useEffect(() => {
    const tick = setInterval(() => {
      setLaneTimers(prev => {
        const next = { ...prev };
        for (const dir in laneActive) {
          if (laneActive[dir]) next[dir]++;
        }
        return next;
      });
      if (codeRed) {
        setCodeRedTimer(p => p + 1);
      }
    }, 1000);
    return () => clearInterval(tick);
  }, [laneActive, codeRed]);

  if (!intersection) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-white dark:bg-slate-950 transition-colors">
        <div className="text-center">
          <div className="w-20 h-20 rounded-full bg-red-50 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
            <XCircle className="w-10 h-10 text-red-400" />
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mb-2">404 — Intersection Not Found</p>
          <p className="text-gray-500 dark:text-gray-400 mb-6 font-mono">Node ID &quot;{String(params?.id)}&quot; does not exist in the system.</p>
          <button onClick={() => router.push("/")} className="px-6 py-2.5 bg-blue-500 text-white rounded-xl font-semibold hover:bg-blue-600 transition-colors">
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const handleSearchSelect = (name: string) => {
    const match = intersections.find((i) => i.name.toLowerCase() === name.toLowerCase());
    if (match) {
      router.push(`/intersection/${match.id}`);
    }
  };

  const handleLanePinResult = (dir: string, ok: boolean) => {
    if (ok) {
      setUnlockedLanes((p) => ({ ...p, [dir]: true }));
      setPinOpenLane(null);
      showToast(`${dir} lane unlocked`, "success");
    } else {
      showToast("Invalid PIN", "error");
    }
  };

  const handleSetLaneState = (dir: string, state: "RED" | "YEL" | "GRN") => {
    setLaneStates((p) => ({ ...p, [dir]: state }));
    if (!laneActive[dir]) {
      setLaneActive(p => ({ ...p, [dir]: true }));
      showToast(`${dir} Override Active → ${state}`, "success");
    } else {
      showToast(`${dir} → ${state}`, "success");
    }
  };

  const handleToggleLaneOverride = (dir: string) => {
    const willBeActive = !laneActive[dir];
    setLaneActive(p => ({ ...p, [dir]: willBeActive }));
    if (!willBeActive) {
      setLaneTimers(p => ({ ...p, [dir]: 0 }));
      showToast(`${dir} Override OFF`, "success");
    } else {
      showToast(`${dir} Override ON`, "success");
    }
  };

  const handleLockLane = (dir: string) => {
    setUnlockedLanes((p) => ({ ...p, [dir]: false }));
  };

  const handleCodeRedPinResult = (ok: boolean) => {
    if (ok) {
      const willBeActive = !codeRed;
      setCodeRed(willBeActive);
      setCodeRedPinOpen(false);
      if (!willBeActive) {
        setCodeRedTimer(0);
      }
      showToast(willBeActive ? "CODE RED ACTIVATED" : "Code Red deactivated", willBeActive ? "error" : "success");
    } else {
      setCodeRedPinOpen(false);
      showToast("Invalid PIN — Code Red unchanged", "error");
    }
  };

  const stateColor = (s: "RED" | "YEL" | "GRN") => {
    if (s === "RED") return "bg-red-500";
    if (s === "YEL") return "bg-amber-400";
    return "bg-green-500";
  };

  return (
    <div className="h-screen w-full flex overflow-hidden bg-white dark:bg-slate-950 transition-colors duration-300">
      {/* ── Left Panel: Command Center (50%) ── */}
      <div className="w-1/2 h-full flex flex-col border-r border-gray-200 dark:border-slate-800">
        {/* Header */}
        <div className="flex-shrink-0 p-5 border-b border-gray-100 dark:border-slate-800 bg-gray-50/80 dark:bg-slate-900/80 flex items-center justify-between transition-colors">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="p-2 rounded-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 hover:bg-gray-100 dark:hover:bg-slate-700/80 transition-colors text-gray-500 dark:text-gray-400 shadow-sm"
            >
              <X className="w-4 h-4" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white leading-tight">{intersection.name}</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">Intersection-I ({intersection.nodeId}) · Command Center</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full animate-pulse ${intersection.status === "Red" ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" : intersection.status === "Yellow" ? "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" : "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]"
              }`} />
            <span className={`text-xs font-bold uppercase tracking-wider ${intersection.status === "Red" ? "text-red-600 dark:text-red-400" : intersection.status === "Yellow" ? "text-amber-600 dark:text-amber-400" : "text-green-600 dark:text-green-400"
              }`}>
              {intersection.status === "Red" ? "Critical" : intersection.status === "Yellow" ? "Moderate" : "Normal"}
            </span>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-5 space-y-6">

            {/* ── 2×2 Camera Grid ── */}
            <section>
              <p className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-widest font-semibold mb-3">Lane Cameras — Live CCTV</p>
              <div className="grid grid-cols-2 gap-3">
                {LANE_DATA.map((lane) => (
                  <CameraFeed key={lane.direction} lane={lane} />
                ))}
              </div>
            </section>

            {/* ── Center Camera & Compass ── */}
            <section>
              <p className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-widest font-semibold mb-3">Center Box Camera & Emergency Compass</p>
              <div className="flex gap-4 items-start">
                <div className="flex-1 relative aspect-[16/7] bg-slate-900 rounded-xl flex items-center justify-center overflow-hidden ring-1 ring-gray-200 dark:ring-slate-700/50 shadow-sm">
                  <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_6px_rgba(59,130,246,0.8)]" />
                    <span className="text-[10px] text-white/80 font-mono uppercase tracking-wider">Center Box</span>
                  </div>
                  <Video className="w-8 h-8 text-slate-700" />
                </div>
                <div className="flex flex-col items-center gap-2.5">
                  <EmergencyCompass onAmbulanceClick={() => setShowAmbulanceModal(true)} />
                  <button
                    onClick={() => setShowAmbulanceModal(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-500/30 rounded-lg text-red-600 dark:text-red-400 text-[10px] font-bold uppercase tracking-wider hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors animate-pulse shadow-sm"
                  >
                    <Siren className="w-3 h-3" />
                    Ambulance Detected
                  </button>
                </div>
              </div>
            </section>

            {/* ══════════════════════════════════════════════════════ */}
            {/* ── SECURE COMMAND CONSOLE: Manual Signal Overrides ── */}
            {/* Adapts seamlessly for light and dark modes!          */}
            {/* ══════════════════════════════════════════════════════ */}
            <section>
              <div className="bg-gray-50 dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-700/50 overflow-hidden shadow-sm dark:shadow-xl transition-colors">
                {/* Console Header */}
                <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-200 dark:border-slate-700/50 bg-gray-100/50 dark:bg-slate-800/60 transition-colors">
                  <Shield className="w-4 h-4 text-blue-500 dark:text-cyan-500" />
                  <p className="text-[10px] text-gray-700 dark:text-cyan-400 uppercase tracking-widest font-bold">Secure Signal Control Console</p>
                  <div className="ml-auto flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[9px] text-gray-400 dark:text-slate-500 font-mono">ONLINE</span>
                  </div>
                </div>

                {/* Lane Rows */}
                <div className="p-4 space-y-2">
                  {["North", "South", "East", "West"].map((dir) => {
                    const current = laneStates[dir];
                    const isUnlocked = unlockedLanes[dir];
                    const isPinOpen = pinOpenLane === dir;
                    const isActive = laneActive[dir];
                    const activeTime = laneTimers[dir];

                    return (
                      <div key={dir} className={`rounded-xl border p-3 transition-colors ${isActive
                        ? "bg-white dark:bg-slate-800 border-blue-200 dark:border-cyan-500/30 shadow-sm"
                        : "bg-white/50 dark:bg-slate-800/50 border-gray-200 dark:border-slate-700/30"
                        }`}>
                        {/* Top row: direction + status + action */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-2.5 h-2.5 rounded-full ${stateColor(current)} shadow-[0_0_6px]`} />
                            <span className="text-sm font-semibold text-gray-800 dark:text-slate-200 w-14 font-mono">{dir}</span>
                            <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${current === "RED" ? "text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
                              : current === "YEL" ? "text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30"
                                : "text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-500/10 border-green-200 dark:border-green-500/30"
                              }`}>{current}</span>
                            <div className={`text-[10px] font-mono px-2 py-0.5 rounded ${isActive ? "bg-blue-50 dark:bg-cyan-900/40 text-blue-700 dark:text-cyan-400 font-bold" : "text-gray-400 dark:text-slate-600"}`}>
                              {activeTime}s active
                            </div>
                          </div>

                          {!isUnlocked && !isPinOpen && (
                            <button
                              onClick={() => setPinOpenLane(dir)}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600/50 rounded-lg text-xs text-gray-500 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors shadow-sm dark:shadow-none"
                            >
                              <Lock className="w-3 h-3" />
                              Unlock Control
                            </button>
                          )}

                          {isPinOpen && (
                            <ConsolePinInput onResult={(ok) => handleLanePinResult(dir, ok)} />
                          )}

                          {isUnlocked && (
                            <div className="flex items-center gap-2">
                              {/* Override Timer Toggle */}
                              <button
                                onClick={() => handleToggleLaneOverride(dir)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-colors shadow-sm ${isActive
                                  ? "bg-blue-500 dark:bg-cyan-600 text-white hover:bg-blue-600 dark:hover:bg-cyan-500"
                                  : "bg-gray-200 dark:bg-slate-700 text-gray-600 dark:text-slate-300 hover:bg-gray-300 dark:hover:bg-slate-600 border border-transparent dark:border-slate-600/50"
                                  }`}
                              >
                                {isActive ? <><Power className="w-3 h-3" /> ON</> : <><Power className="w-3 h-3 text-gray-400" /> OFF</>}
                              </button>

                              <button
                                onClick={() => handleLockLane(dir)}
                                className="flex items-center gap-1 px-2 py-1.5 bg-white dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600/50 rounded-lg text-[10px] font-bold text-gray-500 dark:text-slate-400 hover:bg-gray-50 dark:hover:text-slate-300 transition-colors shadow-sm dark:shadow-none"
                              >
                                <Lock className="w-3 h-3" />
                              </button>
                            </div>
                          )}
                        </div>

                        {/* Expanded Controls (when unlocked) */}
                        {isUnlocked && (
                          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700/30 flex items-center justify-between">
                            {/* State Override Buttons */}
                            <div className="flex items-center gap-2 w-full max-w-[280px]">
                              {([["RED", "🔴", "bg-red-500 hover:bg-red-600 text-white"], ["YEL", "🟡", "bg-amber-500 hover:bg-amber-600 text-white"], ["GRN", "🟢", "bg-green-500 hover:bg-green-600 text-white"]] as const).map(([st, icon, cls]) => (
                                <button
                                  key={st}
                                  onClick={() => handleSetLaneState(dir, st)}
                                  className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all border ${current === st
                                    ? cls + " border-transparent shadow-[0_2px_10px_rgba(0,0,0,0.15)] ring-2 ring-offset-1 ring-offset-white dark:ring-offset-slate-800 ring-" + (st === "RED" ? "red-400" : st === "YEL" ? "amber-400" : "green-400")
                                    : "bg-white dark:bg-slate-700 border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-600"
                                    }`}
                                >
                                  {icon} {st}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Code Red Master Toggle */}
                <div className="px-4 pb-4 mt-2">
                  <div className={`rounded-xl border p-3.5 transition-all shadow-sm ${codeRed
                    ? "bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-500/40"
                    : "bg-white dark:bg-slate-800/50 border-gray-200 dark:border-slate-700/30"
                    }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <AlertTriangle className={`w-4.5 h-4.5 ${codeRed ? "text-red-500 animate-pulse" : "text-gray-400 dark:text-slate-500"}`} />
                        <span className="text-sm font-bold text-gray-800 dark:text-slate-200">CODE RED</span>
                        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${codeRed
                          ? "text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-500/20 border-red-300 dark:border-red-500/40 animate-pulse"
                          : "text-gray-500 dark:text-slate-500 bg-gray-100 dark:bg-slate-700/50 border-gray-200 dark:border-slate-600/30"
                          }`}>{codeRed ? "ACTIVE" : "OFF"}</span>

                        <div className={`ml-2 text-[10px] font-mono px-2 py-0.5 rounded ${codeRed ? "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 font-bold" : "text-gray-400 dark:text-slate-600"}`}>
                          {codeRedTimer}s active
                        </div>
                      </div>

                      {codeRedPinOpen ? (
                        <ConsolePinInput onResult={handleCodeRedPinResult} />
                      ) : (
                        <button
                          onClick={() => setCodeRedPinOpen(true)}
                          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all shadow-sm ${codeRed
                            ? "bg-red-500 dark:bg-red-600 text-white hover:bg-red-600 dark:hover:bg-red-500 shadow-[0_4px_12px_rgba(239,68,68,0.3)]"
                            : "bg-white dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600/50 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
                            }`}
                        >
                          {codeRed ? <Power className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                          {codeRed ? "Turn OFF" : "Activate"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* ── Local Contacts ── */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <Phone className="w-4 h-4 text-gray-400" />
                <p className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-widest font-semibold">Local Emergency Contacts</p>
              </div>
              <div className="space-y-2">
                {LOCAL_CONTACTS.map((c) => (
                  <div key={c.name} className="flex items-center justify-between bg-gray-50 dark:bg-slate-900 rounded-xl border border-gray-100 dark:border-slate-800 px-4 py-3 transition-colors">
                    <div>
                      <p className="text-sm font-medium text-gray-800 dark:text-slate-200">{c.name}</p>
                      <p className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-wider">{c.role}</p>
                    </div>
                    <a
                      href={`tel:${c.phone}`}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-xs font-mono text-gray-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-slate-700 hover:border-blue-200 dark:hover:border-slate-600 hover:text-blue-600 transition-colors shadow-sm"
                    >
                      <Phone className="w-3 h-3" />
                      {c.phone}
                    </a>
                  </div>
                ))}
              </div>
            </section>

          </div>
        </div>
      </div>

      {/* ── Right Panel: Map (50%) ── */}
      <div className="w-1/2 h-full relative">
        {/* Top Overlays matching Dashboard! */}
        <SearchBar onSelect={handleSearchSelect} />
        <ProfileAlerts setActiveTab={() => { }} />

        <MapComponent
          onSelectIntersection={() => { }}
          selectedIntersection={null}
          focusIntersection={intersection.name}
          onFocusHandled={() => { }}
        />
      </div>

      {/* ── Ambulance Modal ── */}
      <AmbulanceModal
        isOpen={showAmbulanceModal}
        onClose={() => setShowAmbulanceModal(false)}
      />

      {/* ── Toast ── */}
      {toast && <Toast toast={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
