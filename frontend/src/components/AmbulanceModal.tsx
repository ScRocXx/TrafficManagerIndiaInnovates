"use client";
import React, { useState } from "react";
import { X, AlertTriangle, ShieldCheck, Activity } from "lucide-react";

interface AmbulanceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

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
            <div className="py-4 text-center">
              <div className="w-20 h-20 mx-auto bg-red-100 rounded-full flex items-center justify-center mb-4 border-4 border-red-50">
                 <Activity className="w-10 h-10 text-red-600 animate-pulse" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Active Preemption</h3>
              <p className="text-sm text-gray-600 px-4 mb-6">
                 An emergency vehicle has been detected approaching the intersection. The Traffic Control System has automatically initiated a signal override to clear the intersection.
              </p>
              
              <div className="bg-gray-50 border border-gray-100 rounded-lg p-4 text-left">
                 <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-semibold text-gray-500 uppercase">Detection Source</span>
                    <span className="text-sm font-bold text-gray-900">AI Edge Node</span>
                 </div>
                 <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-semibold text-gray-500 uppercase">System Status</span>
                    <span className="text-xs font-bold bg-amber-100 text-amber-700 px-2 py-0.5 rounded border border-amber-200">EVP OVERRIDE</span>
                 </div>
                 <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-gray-500 uppercase">Clearance Protocol</span>
                    <span className="text-sm font-bold text-green-600">Executing</span>
                 </div>
              </div>
            </div>
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
