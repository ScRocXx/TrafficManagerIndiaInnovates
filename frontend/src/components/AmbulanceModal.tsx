"use client";
import React, { useState } from "react";
import { X, User, Phone, Building, Hash, AlertTriangle, ShieldCheck } from "lucide-react";

interface AmbulanceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EMERGENCY_LEVEL = 8;

export default function AmbulanceModal({ isOpen, onClose }: AmbulanceModalProps) {
  const [phase, setPhase] = useState<"info" | "otp">("info");
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState(false);

  if (!isOpen) return null;

  const handleClearAlert = () => {
    setPhase("otp");
  };

  const handleVerifyOtp = () => {
    if (otp === "1234") {
      setPhase("info");
      setOtp("");
      setOtpError(false);
      onClose();
    } else {
      setOtpError(true);
      setTimeout(() => setOtpError(false), 1500);
    }
  };

  const handleClose = () => {
    setPhase("info");
    setOtp("");
    setOtpError(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center backdrop-blur-sm bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden border border-gray-100">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100 bg-red-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Ambulance Detected</h2>
              <p className="text-xs text-red-600 font-medium uppercase tracking-wider">Emergency Vehicle Priority</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-full hover:bg-red-100 transition-colors text-gray-500 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5">
          {phase === "info" ? (
            <>
              <div className="flex gap-5">
                {/* Photo Placeholder */}
                <div className="w-28 h-28 rounded-xl bg-gray-100 border-2 border-dashed border-gray-300 flex items-center justify-center flex-shrink-0">
                  <User className="w-10 h-10 text-gray-300" />
                </div>

                {/* Info Fields — using a table-style grid to prevent overlap */}
                <div className="flex-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 items-center">
                  <div className="flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-gray-400" />
                    <span className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Name</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">Rajesh Kumar</span>

                  <div className="flex items-center gap-1.5">
                    <span className="w-3.5 h-3.5 text-center text-[9px] font-bold text-gray-400 leading-[14px]">🎂</span>
                    <span className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Age</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">45 yrs</span>

                  <div className="flex items-center gap-1.5">
                    <Building className="w-3.5 h-3.5 text-gray-400" />
                    <span className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Hospital</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900">AIIMS Trauma Centre</span>

                  <div className="flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5 text-gray-400" />
                    <span className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Reg. ID</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900 font-mono">AMB-DL-4829</span>

                  <div className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-gray-400" />
                    <span className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Contact</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-900 font-mono">+91 98765-43210</span>
                </div>
              </div>

              {/* Emergency Level */}
              <div className="mt-6">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-gray-500 font-semibold uppercase tracking-wider">Emergency Level</p>
                  <p className="text-sm font-bold text-red-600">{EMERGENCY_LEVEL}/10</p>
                </div>
                <div className="flex gap-1.5">
                  {Array.from({ length: 10 }, (_, i) => (
                    <div
                      key={i}
                      className={`h-5 flex-1 rounded-sm transition-colors ${
                        i < EMERGENCY_LEVEL
                          ? i < 4 ? "bg-amber-400" : i < 7 ? "bg-orange-500" : "bg-red-500"
                          : "bg-gray-100 border border-gray-200"
                      }`}
                    />
                  ))}
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-[9px] text-gray-400 font-mono">LOW</span>
                  <span className="text-[9px] text-gray-400 font-mono">CRITICAL</span>
                </div>
              </div>
            </>
          ) : (
            /* OTP Verification Phase */
            <div className="py-4 text-center">
              <ShieldCheck className="w-12 h-12 text-amber-500 mx-auto mb-3" />
              <h3 className="text-base font-bold text-gray-900 mb-1">Admin Verification Required</h3>
              <p className="text-sm text-gray-500 mb-5">Enter Admin Mobile OTP to Clear</p>
              <div className="flex items-center justify-center gap-2 mb-4">
                <input
                  type="text"
                  maxLength={4}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  placeholder="OTP"
                  autoFocus
                  className={`w-28 text-center text-lg font-mono py-2.5 px-4 rounded-xl border-2 outline-none transition-all ${
                    otpError
                      ? "border-red-400 bg-red-50 text-red-600 animate-[shake_0.3s_ease-in-out]"
                      : "border-gray-200 bg-white text-gray-800 focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                  }`}
                  onKeyDown={(e) => e.key === "Enter" && handleVerifyOtp()}
                />
              </div>
              {otpError && <p className="text-xs text-red-500 mb-3 font-medium">Invalid OTP. Try again.</p>}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 pb-5">
          {phase === "info" ? (
            <button
              onClick={handleClearAlert}
              className="w-full py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-semibold text-sm transition-colors"
            >
              Clear Alert and Stop Ambulance Override
            </button>
          ) : (
            <button
              onClick={handleVerifyOtp}
              className="w-full py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-semibold text-sm transition-colors"
            >
              Verify & Clear
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
