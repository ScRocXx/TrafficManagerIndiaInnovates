"use client";
import React, { useState, useEffect, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import {
  X, Phone, Shield, AlertTriangle,
  Video, Lock, Unlock, Siren, CheckCircle, XCircle, Power, FileText
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
  signal: "GRN" | "RED" | "YEL";
  density: string;
  waitTime: string;
  greenTime: string;
}



const LOCAL_CONTACTS = [
  { name: "Traffic Police – Division HQ", phone: "+91 11-2301-5100", role: "Traffic Control" },
  { name: "Fire Station – Sector 4", phone: "+91 11-2336-7800", role: "Fire & Rescue" },
  { name: "Nearest Hospital (LNJP)", phone: "+91 11-2323-4567", role: "Medical Emergency" },
];

const OFFICER_PIN = "1234";
const SUPERVISOR_PIN = "5678";

/* ── Audit Entry ── */
interface AuditEntry {
  time: string;
  dir: string;
  state: string;
  reason: string;
  officer: string;
}

/* ── Camera Feed Placeholder ── */
function CameraFeed({ lane, currentSignal, videoId }: { lane: LaneData; currentSignal: "RED" | "YEL" | "GRN"; videoId: string }) {
  const isGreen = currentSignal === "GRN";
  const isYellow = currentSignal === "YEL";
  const signalLabel = currentSignal === "GRN" ? "GREEN" : currentSignal === "YEL" ? "YELLOW" : "RED";

  return (
    <div className="flex flex-col">
      <div
        className={`relative aspect-video bg-slate-900 rounded-xl flex items-center justify-center overflow-hidden transition-shadow duration-300 group ${isGreen
          ? "ring-2 ring-green-500 shadow-[0_0_15px_rgba(34,197,94,0.4)]"
          : isYellow ? "ring-2 ring-amber-400 shadow-[0_0_15px_rgba(251,191,36,0.4)]"
          : "ring-2 ring-red-500 shadow-[0_0_15px_rgba(239,68,68,0.4)]"
          }`}
      >
        <iframe
          src={`https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1&loop=1&playlist=${videoId}&controls=0&disablekb=1&fs=0&modestbranding=1`}
          className="absolute inset-0 w-full h-full scale-[1.3] pointer-events-none opacity-80 group-hover:opacity-100 transition-opacity"
          allow="autoplay; encrypted-media"
        />
        <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 z-10 bg-black/50 px-2 py-1 rounded backdrop-blur-sm">
          <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${isGreen ? "bg-green-500" : isYellow ? "bg-amber-400" : "bg-red-500"}`} />
          <span className="text-[9px] text-white/90 font-mono uppercase tracking-wider">{lane.direction} CAM</span>
        </div>
        <div className="absolute top-2.5 right-2.5 z-10">
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${isGreen ? "bg-green-500/20 text-green-400 border border-green-500/30" : isYellow ? "bg-amber-500/20 text-amber-500 border border-amber-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"
            }`}>{signalLabel}</span>
        </div>
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
interface ToastData { message: string; type: "success" | "error" | "warning" }

function Toast({ toast, onDone }: { toast: ToastData; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2500);
    return () => clearTimeout(t);
  }, [onDone, toast]);

  return (
    <div className={`fixed top-6 right-6 z-[9998] flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold border transition-all animate-[slideIn_0.3s_ease-out] ${toast.type === "success"
      ? "bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800/50"
      : toast.type === "warning"
        ? "bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800/50"
        : "bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800/50"
      }`}>
      {toast.type === "success" ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
      {toast.message}
    </div>
  );
}

/* ── PIN Input ── */
function PinInput({
  label,
  value,
  onChange,
  hasError,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hasError: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] text-gray-400 dark:text-slate-500 font-medium">{label}</span>
      <input
        type="password"
        maxLength={4}
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, ""))}
        placeholder="PIN"
        className={`w-16 text-center text-xs font-mono py-1.5 px-2 rounded-lg border outline-none transition-all placeholder-gray-300 dark:placeholder-slate-600 bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 ${hasError
          ? "border-red-400 dark:border-red-500"
          : "border-gray-200 dark:border-slate-600 focus:border-blue-400 dark:focus:border-cyan-500"
          }`}
      />
    </div>
  );
}

/* ── Confirm Change Modal ── */
interface ConfirmModalProps {
  dir: string;
  currentState: "RED" | "YEL" | "GRN";
  onConfirm: (reason: string, officerPin: string) => void;
  onCancel: () => void;
}

function ConfirmChangeModal({ dir, currentState, onConfirm, onCancel }: ConfirmModalProps) {
  const [reason, setReason] = useState("");
  const [officerPin, setOfficerPin] = useState("");
  const [errors, setErrors] = useState<{ reason?: string; pin?: string }>({});

  const nextState = currentState === "GRN" ? "RED" : "GRN";

  const handleSubmit = () => {
    const newErrors: { reason?: string; pin?: string } = {};
    if (!reason.trim()) newErrors.reason = "Reason is required.";
    if (officerPin !== OFFICER_PIN) newErrors.pin = "Incorrect PIN.";
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    onConfirm(reason.trim(), officerPin);
  };

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700/40">
      <p className="text-[11px] font-semibold text-gray-700 dark:text-slate-300 mb-2">
        Confirm: {dir} → <span className={nextState === "GRN" ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>{nextState}</span>
      </p>

      {/* PIN Row */}
      <div className="flex items-end gap-3 mb-2">
        <PinInput
          label="Officer PIN"
          value={officerPin}
          onChange={(v) => { setOfficerPin(v); setErrors((e) => ({ ...e, pin: undefined })); }}
          hasError={!!errors.pin}
        />
        {errors.pin && <p className="text-[10px] text-red-500 mb-1.5">{errors.pin}</p>}
      </div>

      {/* Reason */}
      <textarea
        rows={2}
        value={reason}
        onChange={(e) => { setReason(e.target.value); setErrors((e2) => ({ ...e2, reason: undefined })); }}
        placeholder="Reason for change (required)…"
        className={`w-full text-[11px] font-mono py-1.5 px-2.5 rounded-lg border outline-none resize-none transition-all bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 placeholder-gray-300 dark:placeholder-slate-600 mb-1 ${errors.reason ? "border-red-400" : "border-gray-200 dark:border-slate-600 focus:border-blue-400 dark:focus:border-cyan-500"}`}
      />
      {errors.reason && <p className="text-[10px] text-red-500 mb-1">{errors.reason}</p>}

      <div className="flex gap-2 mt-2">
        <button
          onClick={handleSubmit}
          className="flex-1 py-1.5 text-[11px] font-bold uppercase tracking-wider rounded-lg bg-blue-600 dark:bg-cyan-600 text-white hover:bg-blue-700 dark:hover:bg-cyan-500 transition-colors"
        >
          Confirm change
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/* ── Code Red Panel ── */
interface CodeRedPanelProps {
  codeRed: boolean;
  codeRedTimer: number;
  onActivate: () => void;
  onDeactivate: () => void;
  showToast: (msg: string, type: "success" | "error" | "warning") => void;
}

function CodeRedPanel({ codeRed, codeRedTimer, onActivate, onDeactivate, showToast }: CodeRedPanelProps) {
  const [officerPin, setOfficerPin] = useState("");
  const [supervisorPin, setSupervisorPin] = useState("");
  const [holdProgress, setHoldProgress] = useState(0);
  const [isHolding, setIsHolding] = useState(false);
  const [errors, setErrors] = useState<{ officer?: string; supervisor?: string; cooldown?: string }>({});
  const [lastActivatedAt, setLastActivatedAt] = useState<number | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const holdRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startHold = () => {
    // Validate PINs first
    const newErrors: { officer?: string; supervisor?: string; cooldown?: string } = {};
    if (officerPin !== OFFICER_PIN) newErrors.officer = "Incorrect officer PIN.";
    if (supervisorPin !== SUPERVISOR_PIN) newErrors.supervisor = "Incorrect supervisor PIN.";

    // Cooldown check (5 min)
    if (lastActivatedAt && Date.now() - lastActivatedAt < 300000) {
      const remaining = Math.ceil((300000 - (Date.now() - lastActivatedAt)) / 1000);
      newErrors.cooldown = `Cooldown active. Wait ${remaining}s.`;
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsHolding(true);
    setHoldProgress(0);
    holdRef.current = setInterval(() => {
      setHoldProgress((p) => {
        if (p >= 100) {
          clearInterval(holdRef.current!);
          setIsHolding(false);
          setHoldProgress(0);
          triggerActivation();
          return 100;
        }
        return p + 3.5;
      });
    }, 100);
  };

  const endHold = () => {
    if (holdRef.current) clearInterval(holdRef.current);
    if (isHolding) {
      setIsHolding(false);
      setHoldProgress(0);
    }
  };

  const triggerActivation = () => {
    setLastActivatedAt(Date.now());
    onActivate();
    setOfficerPin("");
    setSupervisorPin("");
    // 10s cancellation countdown
    let secs = 10;
    setCountdown(secs);
    countdownRef.current = setInterval(() => {
      secs--;
      setCountdown(secs);
      if (secs <= 0) {
        clearInterval(countdownRef.current!);
        setCountdown(null);
      }
    }, 1000);
  };

  const handleDeactivate = () => {
    if (countdownRef.current) clearInterval(countdownRef.current);
    setCountdown(null);
    onDeactivate();
  };

  return (
    <div className={`rounded-xl border p-3.5 transition-all ${codeRed
      ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-500/40"
      : "bg-white dark:bg-slate-800/50 border-gray-200 dark:border-slate-700/30"
      }`}>
      {/* Header row */}
      <div className="flex items-center gap-2.5 mb-3">
        <AlertTriangle className={`w-4 h-4 ${codeRed ? "text-red-500 animate-pulse" : "text-gray-400 dark:text-slate-500"}`} />
        <span className="text-sm font-bold text-gray-800 dark:text-slate-200 font-mono">CODE RED</span>
        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${codeRed
          ? "text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-500/20 border-red-300 dark:border-red-500/40 animate-pulse"
          : "text-gray-500 dark:text-slate-500 bg-gray-100 dark:bg-slate-700/50 border-gray-200 dark:border-slate-600/30"
          }`}>{codeRed ? "ACTIVE" : "OFF"}</span>
        {codeRed && (
          <span className="ml-1 text-[10px] font-mono px-2 py-0.5 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 font-bold">
            {codeRedTimer}s active
          </span>
        )}
      </div>

      {/* Description */}
      {!codeRed && (
        <p className="text-[11px] text-gray-400 dark:text-slate-500 mb-3 leading-relaxed">
          Requires officer + supervisor PINs. Hold button for 3s to activate. Cannot reactivate within 5 minutes.
        </p>
      )}

      {/* ACTIVE state */}
      {codeRed && (
        <div className="mb-3">
          {countdown !== null && (
            <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-500/30">
              <span className="text-[11px] text-red-600 dark:text-red-400 font-mono">Cancel window:</span>
              <span className="text-lg font-bold text-red-600 dark:text-red-400 font-mono">{countdown}s</span>
            </div>
          )}
          <button
            onClick={handleDeactivate}
            className="w-full py-2 text-[11px] font-bold uppercase tracking-wider rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors flex items-center justify-center gap-2"
          >
            <Power className="w-3.5 h-3.5" />
            Deactivate Code Red
          </button>
        </div>
      )}

      {/* INACTIVE state — PIN inputs + hold button */}
      {!codeRed && (
        <>
          <div className="flex items-end gap-4 mb-2">
            <PinInput
              label="Officer PIN"
              value={officerPin}
              onChange={(v) => { setOfficerPin(v); setErrors((e) => ({ ...e, officer: undefined })); }}
              hasError={!!errors.officer}
            />
            <PinInput
              label="Supervisor PIN"
              value={supervisorPin}
              onChange={(v) => { setSupervisorPin(v); setErrors((e) => ({ ...e, supervisor: undefined })); }}
              hasError={!!errors.supervisor}
            />
          </div>

          {/* Error messages */}
          {errors.officer && <p className="text-[10px] text-red-500 mb-1">{errors.officer}</p>}
          {errors.supervisor && <p className="text-[10px] text-red-500 mb-1">{errors.supervisor}</p>}
          {errors.cooldown && <p className="text-[10px] text-amber-500 mb-1">{errors.cooldown}</p>}

          {/* Hold-to-activate button */}
          <div className="relative mt-3 overflow-hidden rounded-lg">
            <div
              className="absolute left-0 top-0 h-full bg-red-200 dark:bg-red-500/20 transition-none rounded-lg"
              style={{ width: `${holdProgress}%` }}
            />
            <button
              onMouseDown={startHold}
              onMouseUp={endHold}
              onMouseLeave={endHold}
              onTouchStart={startHold}
              onTouchEnd={endHold}
              className="relative w-full py-2 text-[11px] font-bold uppercase tracking-wider rounded-lg border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors flex items-center justify-center gap-2 select-none"
            >
              <Lock className="w-3.5 h-3.5" />
              {isHolding
                ? `Hold… ${Math.round(holdProgress)}%`
                : "Hold to activate"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/* ── Audit Log ── */
function AuditLog({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) return null;
  return (
    <section>
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-gray-400" />
        <p className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-widest font-semibold">Audit Log</p>
      </div>
      <div className="bg-gray-50 dark:bg-slate-900 rounded-xl border border-gray-100 dark:border-slate-800 overflow-hidden">
        {entries.map((e, i) => (
          <div key={i} className={`flex items-start gap-3 px-4 py-2.5 text-[11px] font-mono ${i < entries.length - 1 ? "border-b border-gray-100 dark:border-slate-800" : ""}`}>
            <span className="text-gray-400 dark:text-slate-600 min-w-[52px]">{e.time}</span>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider min-w-[28px] text-center ${e.state === "GRN" || e.state === "DEACT"
              ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
              : e.state === "CODE RED"
                ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                : "bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400"
              }`}>{e.state}</span>
            <span className="text-gray-600 dark:text-slate-400 flex-1">{e.dir} — {e.reason}</span>
          </div>
        ))}
      </div>
    </section>
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
    "01": "GRN", "02": "RED", "03": "RED", "04": "RED",
  });
  
  const [laneGreenTimers, setLaneGreenTimers] = useState<Record<string, number>>({
    "01": 45, "02": 0, "03": 0, "04": 0
  });
  const [laneWaitTimers, setLaneWaitTimers] = useState<Record<string, number>>({
    "01": 0, "02": 32, "03": 48, "04": 20
  });
  const [laneDensities, setLaneDensities] = useState<Record<string, string>>({
    "01": "0%", "02": "0%", "03": "0%", "04": "0%"
  });
  const [evpCount, setEvpCount] = useState<number>(0);

  // Timers and Overrides
  const [laneActive, setLaneActive] = useState<Record<string, boolean>>({
    "01": false, "02": false, "03": false, "04": false,
  });
  const [laneTimers, setLaneTimers] = useState<Record<string, number>>({
    "01": 0, "02": 0, "03": 0, "04": 0,
  });
  const [unlockedLanes, setUnlockedLanes] = useState<Record<string, boolean>>({
    "01": false, "02": false, "03": false, "04": false,
  });
  const [pinOpenLane, setPinOpenLane] = useState<string | null>(null);
  const [confirmChangeLane, setConfirmChangeLane] = useState<string | null>(null);

  // Audit log
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([
    { time: "09:12", dir: "01", state: "GRN", reason: "Morning clearance", officer: "Officer #214" },
    { time: "08:55", dir: "02", state: "RED", reason: "Accident reported", officer: "Officer #214" },
  ]);

  // Code Red
  const [codeRed, setCodeRed] = useState(false);
  const [codeRedTimer, setCodeRedTimer] = useState<number>(0);

  // Live status from API
  const [liveStatus, setLiveStatus] = useState<string>("Green");

  const id = params?.id as string;
  const intersection = intersections.find((i) => i.nodeId === id || i.id === Number(id));

  const showToast = useCallback((message: string, type: "success" | "error" | "warning") => {
    setToast({ message, type });
  }, []);

  const addAudit = useCallback((dir: string, state: string, reason: string) => {
    const now = new Date();
    const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setAuditLog((prev) => [{ time, dir, state, reason, officer: "Officer #214" }, ...prev]);
  }, []);

  const prevPhaseRef = useRef<string>("");

  useEffect(() => {
    if (!intersection?.nodeId) return;
    
    const fetchTraffic = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://india-innovate-backend.onrender.com";
        const res = await fetch(`${API_URL}/api/traffic/${intersection.nodeId}`);
        if (!res.ok) return;
        const data = await res.json();
        
        let newLaneStates: Record<string, "RED" | "YEL" | "GRN"> = { "01": "RED", "02": "RED", "03": "RED", "04": "RED" };
        const activePhaseFull = data.state_snapshot?.active_phase;
        const currentPhase = activePhaseFull || "";
        const phaseChanged = currentPhase !== prevPhaseRef.current;
        prevPhaseRef.current = currentPhase;

        if (activePhaseFull) {
          const suffix = activePhaseFull.split("-").pop() || "";
          const mappedDir = suffix || "01";
          
          let engineState = data.state_snapshot?.engine_state || "BASE_GREEN";
          if (engineState.includes("YELLOW") || engineState.includes("YEL")) {
             newLaneStates[mappedDir] = "YEL";
          } else {
             newLaneStates[mappedDir] = "GRN";
             const gt = data.state_snapshot?.green_timer;
             if (typeof gt === "number") {
               setLaneGreenTimers(prev => ({ ...prev, [mappedDir]: gt }));
             }
          }
        }
        
        setLaneStates(newLaneStates as Record<string, "RED" | "YEL" | "GRN">);
        
        if (data.lane_metrics) {
          let newDensities = { ...laneDensities };
          for (const key in data.lane_metrics) {
            const laneObj = data.lane_metrics[key];
            const suffix = key.split("-").pop() || "";
            const dir = suffix;
            if (dir) {
              const q = laneObj.queue_N || 0;
              newDensities[dir] = `${Math.min(100, Math.round((q / 120) * 100))}%`;
            }
          }
          setLaneDensities(newDensities);

          // Continuously sync wait timers from Jetson payload
          let newWait: Record<string, number> = {};
          for (const key in data.lane_metrics) {
            const laneObj = data.lane_metrics[key];
            const suffix = key.split("-").pop() || "";
            if (suffix) {
              newWait[suffix] = laneObj.wait_time_T || 0;
            }
          }
          // The fetch logic provides the baseline.
          setLaneWaitTimers((prev) => {
            // Only update if Jetson gives a strictly higher value, preventing explicit 0 overwrites on RED lanes
            const updated = { ...prev };
            Object.keys(newWait).forEach(k => {
              if (newWait[k] > (updated[k] || 0)) {
                updated[k] = newWait[k];
              }
            });
            return updated;
          });
        }
        
        setEvpCount(data.critical_events?.evp_overrides || 0);
        setLiveStatus(data.status || "Green");

      } catch (err) {
        console.error(err);
      }
    };

    fetchTraffic();
    const interval = setInterval(fetchTraffic, 1500);
    return () => clearInterval(interval);
  }, [intersection]);

  // Global Tick for Timers
  useEffect(() => {
    const tick = setInterval(() => {
      setLaneTimers(prev => {
        const next: Record<string, number> = { ...prev };
        for (const dir in laneActive) {
          if (laneActive[dir]) next[dir]++;
        }
        return next;
      });
      if (codeRed) {
        setCodeRedTimer(p => p + 1);
      }
      
      setLaneGreenTimers(prev => {
        const n: Record<string, number> = { ...prev };
        for (const dir in laneStates) {
          if (laneStates[dir] === "GRN" && (n[dir] || 0) > 0) {
            n[dir]--;
          }
        }
        return n;
      });

      // Wait timers: tick UP for RED lanes (accumulating wait time), reset for GREEN
      setLaneWaitTimers(prev => {
        const n: Record<string, number> = { ...prev };
        for (const dir in laneStates) {
          if (laneStates[dir] === "RED") {
            n[dir] = (n[dir] || 0) + 1;  // Counting up while vehicles wait
          } else if (laneStates[dir] === "GRN") {
            n[dir] = 0; // Green = no wait
          }
        }
        return n;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, [laneActive, codeRed, laneStates]);

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
    if (match) router.push(`/intersection/${match.nodeId}`);
  };

  /* ── Lane PIN unlock ── */
  const handleLanePinResult = (dir: string, ok: boolean) => {
    if (ok) {
      setUnlockedLanes((p) => ({ ...p, [dir]: true }));
      setPinOpenLane(null);
      showToast(`${dir} lane unlocked`, "success");
    } else {
      showToast("Invalid PIN", "error");
    }
  };

  /* ── Signal state change (after confirm modal) ── */
  const handleConfirmedChange = (dir: string, reason: string) => {
    const cur = laneStates[dir];
    const next: "RED" | "GRN" = cur === "GRN" ? "RED" : "GRN";
    
    setLaneStates((p) => {
      const newState = { ...p };
      if (next === "GRN") {
        // Enforce only one green light at a time
        Object.keys(newState).forEach(k => {
          if (k !== dir) newState[k] = "RED";
        });
      }
      newState[dir] = next;
      return newState;
    });

    if (next === "GRN") {
      setLaneGreenTimers(p => ({ ...p, [dir]: 45 }));
      setLaneWaitTimers(p => ({ ...p, [dir]: 0 }));
    }

    // Send Jetson API Call
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://india-innovate-backend.onrender.com";
    fetch(`${API_URL}/api/override`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nodeId: intersection?.nodeId || "unknown", lane: dir, state: next, reason })
    }).catch(e => console.error("Failed to signal Jetson", e));

    if (!laneActive[dir]) setLaneActive((p) => ({ ...p, [dir]: true }));
    setConfirmChangeLane(null);
    addAudit(dir, next, reason);
    showToast(`${dir} → ${next}`, "success");
  };

  /* ── Quick state switch (Unlocked Mode) ── */
  const handleQuickSwitch = (dir: string, targetState: "RED" | "YEL" | "GRN") => {
    if (laneStates[dir] === targetState) return;
    
    setLaneStates((p) => {
      const newState = { ...p };
      if (targetState === "GRN" || targetState === "YEL") {
        // Ensure standard intersection safety (no concurrent greens in cross traffic)
        Object.keys(newState).forEach(k => {
          if (k !== dir) newState[k] = "RED"; 
        });
      }
      newState[dir] = targetState;
      return newState;
    });

    if (targetState === "GRN") {
      setLaneGreenTimers(p => ({ ...p, [dir]: 45 }));
      setLaneWaitTimers(p => ({ ...p, [dir]: 0 }));
    }

    // Send Jetson API Call
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://india-innovate-backend.onrender.com";
    fetch(`${API_URL}/api/override`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nodeId: intersection?.nodeId || "unknown", lane: dir, state: targetState, reason: "Manual Quick Switch" })
    }).catch(e => console.error("Failed to signal Jetson", e));

    addAudit(dir, targetState, "Manual quick switch (Unlocked)");
    showToast(`${dir} manually set to ${targetState}`, "success");
  };

  /* ── Override toggle ── */
  const handleToggleLaneOverride = (dir: string) => {
    const willBeActive = !laneActive[dir];
    setLaneActive((p) => ({ ...p, [dir]: willBeActive }));
    if (!willBeActive) {
      setLaneTimers((p) => ({ ...p, [dir]: 0 }));
      showToast(`${dir} Override OFF`, "success");
    } else {
      showToast(`${dir} Override ON`, "success");
    }
  };

  const handleLockLane = (dir: string) => {
    setUnlockedLanes((p) => ({ ...p, [dir]: false }));
    setConfirmChangeLane(null);
  };

  const stateColor = (s: "RED" | "YEL" | "GRN") => {
    if (s === "RED") return "bg-red-500";
    if (s === "YEL") return "bg-amber-400";
    return "bg-green-500";
  };

  return (
    <div className="h-screen w-full flex overflow-hidden bg-white dark:bg-slate-950 transition-colors duration-300">
      <style dangerouslySetInnerHTML={{
        __html: `
        @keyframes dashboardOpenPulse {
          0% { box-shadow: inset 0 0 0 4px transparent, 0 0 0 0 rgba(59,130,246,0); transform: translateX(-20px); opacity: 0; }
          30% { transform: translateX(0); opacity: 1; }
          40% { box-shadow: inset 0 0 0 4px rgba(59,130,246,0.5), 0 0 20px 10px rgba(59,130,246,0.3); }
          100% { box-shadow: inset 0 0 0 4px transparent, 0 0 0 0 rgba(59,130,246,0); }
        }
        .anim-dashboard-open {
          animation: dashboardOpenPulse 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}} />

      {/* ── Left Panel: Command Center (50%) ── */}
      <div className="w-1/2 h-full flex flex-col border-r border-gray-200 dark:border-slate-800 anim-dashboard-open relative z-10 bg-white dark:bg-slate-950">
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
              <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">Node NB-{intersection.nodeId} · Command Center</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full animate-pulse ${liveStatus === "Red" ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" : liveStatus === "Yellow" ? "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" : "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]"}`} />
            <span className={`text-xs font-bold uppercase tracking-wider ${liveStatus === "Red" ? "text-red-600 dark:text-red-400" : liveStatus === "Yellow" ? "text-amber-600 dark:text-amber-400" : "text-green-600 dark:text-green-400"}`}>
              {liveStatus === "Red" ? "Critical" : liveStatus === "Yellow" ? "Moderate" : "Normal"}
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
                {["01", "02", "03", "04"].map((dir, idx) => {
                  const current = codeRed ? "RED" : laneStates[dir];
                  const waitVal = current === "RED" ? `${laneWaitTimers[dir]}s` : "0s";
                  const greenVal = current === "GRN" ? `${laneGreenTimers[dir]}s` : "—";
                  const density = laneDensities[dir] || "0%";
                  const lane = { direction: `Camera ${dir}`, density, waitTime: waitVal, greenTime: greenVal, signal: current as "RED" | "YEL" | "GRN" };
                  
                  // Fallback IDs if they want 4 different angles
                  const vidId = intersection.videoId || "1EiC9bvVGnk";
                  return (
                    <CameraFeed key={lane.direction} lane={lane} currentSignal={laneStates[dir]} videoId={vidId} />
                  );
                })}
              </div>
            </section>

            {/* ── Center Camera & Compass ── */}
            <section>
              <p className="text-[10px] text-gray-400 dark:text-slate-500 uppercase tracking-widest font-semibold mb-3">Center Box Camera & Emergency Compass</p>
              <div className="flex gap-4 items-start">
                <div className="flex-1 relative aspect-[16/7] bg-slate-900 rounded-xl flex items-center justify-center overflow-hidden shadow-sm group">
                  <iframe
                    src={`https://www.youtube.com/embed/${intersection.videoId || "1EiC9bvVGnk"}?autoplay=1&mute=1&loop=1&playlist=${intersection.videoId || "1EiC9bvVGnk"}&controls=0&disablekb=1&fs=0&modestbranding=1`}
                    className="absolute inset-0 w-full h-full scale-[1.3] pointer-events-none opacity-80 group-hover:opacity-100 transition-opacity"
                    allow="autoplay; encrypted-media"
                  />
                  <div className="absolute top-3 left-3 flex items-center gap-2 z-10 bg-black/60 px-3 py-1.5 rounded-lg backdrop-blur-sm border border-white/10">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_6px_rgba(239,68,68,0.8)]" />
                    <span className="text-[10px] text-white/90 font-mono uppercase tracking-widest font-bold">Center PTZ Live</span>
                  </div>
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
            {/* ── SECURE COMMAND CONSOLE ──                         */}
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
                    <span className="ml-2 text-[9px] text-gray-400 dark:text-slate-500 font-mono border border-gray-200 dark:border-slate-600 px-1.5 py-0.5 rounded">Morning Shift</span>
                  </div>
                </div>

                {/* Lane Rows */}
                <div className="p-4 space-y-2">
                  {["01", "02", "03", "04"].map((dir) => {
                    const current = laneStates[dir];
                    const isUnlocked = unlockedLanes[dir];
                    const isPinOpen = pinOpenLane === dir;
                    const isActive = laneActive[dir];
                    const activeTime = laneTimers[dir];
                    const isConfirming = confirmChangeLane === dir;

                    return (
                      <div key={dir} className={`rounded-xl border transition-colors ${isActive
                        ? "bg-white dark:bg-slate-800 border-blue-200 dark:border-cyan-500/30 shadow-sm"
                        : "bg-white/50 dark:bg-slate-800/50 border-gray-200 dark:border-slate-700/30"
                        }`}>
                        {/* Top row */}
                        <div className="flex items-center justify-between p-3">
                          <div className="flex items-center gap-3">
                            <div className={`w-2.5 h-2.5 rounded-full ${stateColor(current)} shadow-[0_0_6px]`} />
                            <span className="text-sm font-semibold text-gray-800 dark:text-slate-200 w-14 font-mono">{dir}</span>
                            <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${current === "RED"
                              ? "text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-500/10 border-red-200 dark:border-red-500/30"
                              : current === "YEL"
                                ? "text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30"
                                : "text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-500/10 border-green-200 dark:border-green-500/30"
                              }`}>{current}</span>
                            <div className={`text-[10px] font-mono px-2 py-0.5 rounded ${isActive
                              ? "bg-blue-50 dark:bg-cyan-900/40 text-blue-700 dark:text-cyan-400 font-bold"
                              : "text-gray-400 dark:text-slate-600"}`}>
                              {activeTime}s active
                            </div>
                          </div>

                          {/* Right side controls */}
                          {!isUnlocked && !isPinOpen && (
                            <button
                              onClick={() => setPinOpenLane(dir)}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600/50 rounded-lg text-xs text-gray-500 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
                            >
                              <Lock className="w-3 h-3" />
                              Unlock Control
                            </button>
                          )}

                          {/* PIN entry */}
                          {isPinOpen && (
                            <div className="flex items-center gap-2">
                              <Lock className="w-3 h-3 text-gray-400" />
                              <input
                                type="password"
                                maxLength={4}
                                placeholder="PIN"
                                autoFocus
                                className="w-16 text-center text-xs font-mono py-1.5 px-2 rounded-lg border border-gray-200 dark:border-slate-600 outline-none bg-white dark:bg-slate-800 text-gray-800 dark:text-slate-200 focus:border-blue-400 dark:focus:border-cyan-500"
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") handleLanePinResult(dir, (e.target as HTMLInputElement).value === OFFICER_PIN);
                                }}
                              />
                              <button
                                onClick={(e) => {
                                  const input = (e.currentTarget.previousSibling as HTMLInputElement);
                                  handleLanePinResult(dir, input.value === OFFICER_PIN);
                                }}
                                className="text-[10px] px-2.5 py-1.5 bg-blue-600 dark:bg-cyan-600 text-white rounded-md font-semibold"
                              >
                                OK
                              </button>
                              <button
                                onClick={() => setPinOpenLane(null)}
                                className="text-[10px] px-2 py-1.5 bg-gray-100 dark:bg-slate-700 text-gray-500 rounded-md"
                              >
                                ✕
                              </button>
                            </div>
                          )}

                          {/* Unlocked controls */}
                          {isUnlocked && (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleToggleLaneOverride(dir)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-colors shadow-sm ${isActive
                                  ? "bg-blue-500 dark:bg-cyan-600 text-white hover:bg-blue-600"
                                  : "bg-gray-200 dark:bg-slate-700 text-gray-600 dark:text-slate-300 hover:bg-gray-300 dark:hover:bg-slate-600 border border-transparent dark:border-slate-600/50"
                                  }`}
                              >
                                <Power className="w-3 h-3" />
                                {isActive ? "ON" : "OFF"}
                              </button>
                              <button
                                onClick={() => handleLockLane(dir)}
                                className="flex items-center gap-1 px-2 py-1.5 bg-white dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600/50 rounded-lg text-[10px] text-gray-500 dark:text-slate-400 hover:bg-gray-50 transition-colors shadow-sm"
                              >
                                <Lock className="w-3 h-3" />
                              </button>
                            </div>
                          )}
                        </div>

                        {/* Expanded controls when unlocked */}
                        {isUnlocked && (
                          <div className="px-3 pb-3 border-t border-gray-100 dark:border-slate-700/30 pt-3 mt-0">
                            {/* Signal state buttons */}
                            <div className="flex items-center gap-2 mb-2">
                              {([
                                ["RED", "bg-red-500 hover:bg-red-600 text-white", "ring-red-400"],
                                ["YEL", "bg-amber-500 hover:bg-amber-600 text-white", "ring-amber-400"],
                                ["GRN", "bg-green-500 hover:bg-green-600 text-white", "ring-green-400"],
                              ] as const).map(([st, cls, ring]) => (
                                <button
                                  key={st}
                                  onClick={() => handleQuickSwitch(dir, st)}
                                  className={`flex-1 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all border ${current === st
                                    ? `${cls} border-transparent shadow ring-2 ring-offset-1 ring-offset-white dark:ring-offset-slate-800 ${ring}`
                                    : "bg-white dark:bg-slate-700 border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-600"
                                    }`}
                                >
                                  {st}
                                </button>
                              ))}
                            </div>

                            {/* Confirm change modal */}
                            {isConfirming && (
                              <ConfirmChangeModal
                                dir={dir}
                                currentState={current}
                                onConfirm={(reason) => handleConfirmedChange(dir, reason)}
                                onCancel={() => setConfirmChangeLane(null)}
                              />
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Code Red */}
                <div className="px-4 pb-4">
                  <CodeRedPanel
                    codeRed={codeRed}
                    codeRedTimer={codeRedTimer}
                    onActivate={() => {
                      setCodeRed(true);
                      setCodeRedTimer(0);
                      addAudit("All lanes", "CODE RED", "Code Red activated — Officer #214 + Supervisor #08");
                      showToast("CODE RED ACTIVATED", "error");
                    }}
                    onDeactivate={() => {
                      setCodeRed(false);
                      setCodeRedTimer(0);
                      addAudit("All lanes", "DEACT", "Code Red deactivated");
                      showToast("Code Red deactivated", "success");
                    }}
                    showToast={showToast}
                  />
                </div>
              </div>
            </section>

            {/* ── Audit Log ── */}
            <AuditLog entries={auditLog} />

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
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-xs font-mono text-gray-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-slate-700 hover:border-blue-200 hover:text-blue-600 transition-colors shadow-sm"
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
        <div className="absolute top-6 inset-x-6 z-[1000] flex items-start justify-between gap-4 pointer-events-none">
          <div className="flex-1 hidden md:block" />
          <div className="pointer-events-auto w-full max-w-[400px]">
            <SearchBar onSelect={handleSearchSelect} className="w-full" />
          </div>
          <div className="flex-1 flex justify-end pointer-events-auto">
            <ProfileAlerts setActiveTab={() => { }} className="" />
          </div>
        </div>
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