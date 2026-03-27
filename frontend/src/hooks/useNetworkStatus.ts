"use client";
import { useState, useEffect, useMemo } from "react";
import { intersections, IntersectionData } from "@/lib/intersections";

/* ── Types ── */
export interface LaneData {
  density: number;
  wait_time: number;
}

export interface NodeData {
  node_id: string;
  hardware_status: string;
  lanes: Record<string, LaneData>;
}

export interface EnrichedIntersection extends IntersectionData {
  status: "Red" | "Yellow" | "Green";
  p: number;
}

export interface DeviceStatus {
  id: string;
  device: string;
  type: "camera" | "sensor" | "controller";
  location: string;
  status: "online" | "offline" | "degraded";
  uptime: string;
  lastPing: string;
  firmware: string;
  issues: string[];
}

export interface VulnerabilityData {
  id: string;
  type: string;
  status: string;
  last_ping: string;
  issue: string;
  location: string;
}

/* ── Deterministic device simulation ── */
const DEVICE_TYPES: ("camera" | "sensor" | "controller")[] = ["camera", "sensor", "controller"];
const DEVICE_NAMES: Record<string, string[]> = {
  camera: ["PTZ Camera Alpha", "Fixed Camera C1", "Thermal Camera T1", "PTZ Camera Beta", "Wide-Angle Cam W1"],
  sensor: ["Inductive Loop Sensor", "Radar Detector R1", "Piezoelectric Sensor", "LiDAR Scanner L1", "Microwave Sensor M1"],
  controller: ["Signal Controller Unit", "Edge Controller EC1", "Relay Controller RC1", "Phase Timer PT1", "Traffic Signal TSU"],
};
const FIRMWARE_VERSIONS = ["v3.2.1", "v3.3.0", "v4.0.0", "v5.0.1", "v5.1.0", "v2.4.2", "v2.1.0", "v1.9.8"];
const POSSIBLE_ISSUES: Record<string, string[]> = {
  offline: ["Connection timeout", "Power supply unstable", "Hardware replacement needed", "Inductive loop failure"],
  degraded: ["High latency", "Network congestion detected", "Intermittent signal loss", "Phase timing desync", "Thermal throttling"],
  online: [],
};

function generateDevicesForIntersections(tick: number): DeviceStatus[] {
  const allDevices: DeviceStatus[] = [];
  intersections.forEach((intersection, idx) => {
    const seed = parseInt(intersection.nodeId.slice(-3)) || 100;
    // Each intersection gets 2-3 devices
    const numDevices = 2 + (seed % 2);
    for (let d = 0; d < numDevices; d++) {
      const typeIdx = (seed + d) % 3;
      const type = DEVICE_TYPES[typeIdx];
      const namePool = DEVICE_NAMES[type];
      const deviceName = namePool[(seed + d) % namePool.length];
      const prefix = type === "camera" ? "CAM" : type === "sensor" ? "SEN" : "CTR";
      const deviceId = `${prefix}-${String(idx * 3 + d + 1).padStart(3, "0")}`;

      // Time-varying status: mix tick into the seed so ~2-3 devices shift each cycle
      const statusSeed = (seed + d * 7 + tick * 3) % 20;
      const status: "online" | "offline" | "degraded" =
        statusSeed < 2 ? "offline" : statusSeed < 5 ? "degraded" : "online";

      const issues = status === "online" ? [] :
        POSSIBLE_ISSUES[status].filter((_, i) => (seed + d + i + tick) % 3 === 0).slice(0, 2);

      // Dynamic "last ping" based on tick
      const pingSeconds = status === "online" ? ((tick * 2 + seed) % 8) + 1 : undefined;

      allDevices.push({
        id: deviceId,
        device: deviceName,
        type,
        location: intersection.name,
        status,
        uptime: status === "offline" ? "0%" : status === "degraded" ? `${72 + (seed % 20)}%` : `${96 + (seed % 4)}.${seed % 10}%`,
        lastPing: status === "offline" ? `${5 + ((seed + tick) % 40)} min ago` : status === "degraded" ? `${1 + ((seed + tick) % 14)} min ago` : `${pingSeconds} sec ago`,
        firmware: FIRMWARE_VERSIONS[(seed + d) % FIRMWARE_VERSIONS.length],
        issues,
      });
    }
  });
  return allDevices;
}

function generateVulnerabilities(devices: DeviceStatus[]): VulnerabilityData[] {
  return devices
    .filter(d => d.status === "offline" || (d.status === "degraded" && d.issues.length > 0))
    .map(d => ({
      id: d.id,
      type: d.type === "camera" ? "Camera Fault" : d.type === "sensor" ? "Sensor Fault" : "Controller Fault",
      status: d.status === "offline" ? "Critical" : "Warning",
      last_ping: d.lastPing,
      issue: d.issues[0] || "Unknown issue",
      location: d.location,
    }));
}

/* ── Hook ── */
export function useNetworkStatus() {
  const [nodes, setNodes] = useState<(NodeData | null)[]>([]);
  const [liveTraffic, setLiveTraffic] = useState<Record<string, { status: string; congestionLevel: number; vehiclesPassed: number }>>({});
  const [liveDevices, setLiveDevices] = useState<DeviceStatus[]>([]);
  const [tick, setTick] = useState(0);

  // Device simulation ticker — shifts statuses every 8 seconds
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 8000);
    return () => clearInterval(interval);
  }, []);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://india-innovate-backend.onrender.com";

  // Fetch simulated network status for ALL nodes (from simulation backend)
  useEffect(() => {
    const fetchNetworkStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/api/network-status`);
        if (res.ok) {
          const data = await res.json();
          if (data.nodes) {
            setNodes(data.nodes);
          }
        }
      } catch {
        // Silently fallback — generate deterministic mock nodes
        const mockNodes: NodeData[] = intersections.map((item, idx) => {
          const seed = parseInt(item.nodeId.slice(-3)) || 100;
          const density = (seed % 10 < 2) ? 75 + (seed % 15) : (seed % 10 < 5) ? 45 + (seed % 20) : 15 + (seed % 25);
          return {
            node_id: `Node_${idx + 1}`,
            hardware_status: "ONLINE",
            lanes: {
              N: { density, wait_time: Math.floor(10 + (seed % 40)) },
              S: { density: Math.max(10, density - 10), wait_time: Math.floor(10 + (seed % 30)) },
              E: { density: Math.max(10, density + 5), wait_time: Math.floor(15 + (seed % 35)) },
              W: { density: Math.max(10, density - 5), wait_time: Math.floor(12 + (seed % 25)) },
            }
          };
        });
        setNodes(mockNodes);
      }
    };
    fetchNetworkStatus();
    const interval = setInterval(fetchNetworkStatus, 5000);
    return () => clearInterval(interval);
  }, [API_URL]);

  // Fetch real DB traffic data for intersections with live Jetson data
  useEffect(() => {
    const fetchLive = async () => {
      try {
        const res = await fetch(`${API_URL}/api/traffic`);
        if (res.ok) {
          const data = await res.json();
          const statusMap: Record<string, { status: string; congestionLevel: number; vehiclesPassed: number }> = {};
          /* eslint-disable @typescript-eslint/no-explicit-any */
          data.forEach((d: any) => {
            statusMap[d.nodeId] = {
              status: d.status || "Green",
              congestionLevel: d.congestionLevel || 0,
              vehiclesPassed: d.vehiclesPassed || 0,
            };
          });
          setLiveTraffic(statusMap);
        }
      } catch {
        // Silently fallback
      }
    };
    fetchLive();
    const interval = setInterval(fetchLive, 5000);
    return () => clearInterval(interval);
  }, [API_URL]);

  // Fetch live device health data from DB, merge with simulated
  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const res = await fetch(`${API_URL}/api/devices`);
        if (res.ok) {
          const data: any[] = await res.json();
          // Convert backend device format to DeviceStatus
          const live: DeviceStatus[] = data.map((d: any) => ({
            id: d.id,
            device: d.id, // Use ID as name if no name field
            type: (d.type || "controller") as "camera" | "sensor" | "controller",
            location: "Live Node",
            status: d.status as "online" | "offline" | "degraded",
            uptime: d.uptime || "N/A",
            lastPing: d.lastPing || "N/A",
            firmware: d.firmware || "unknown",
            issues: d.issues || [],
          }));
          setLiveDevices(live);
        }
      } catch {
        // Silently fallback to simulated only
      }
    };
    fetchDevices();
    const interval = setInterval(fetchDevices, 10000);
    return () => clearInterval(interval);
  }, [API_URL]);

  // Enriched intersection data: merge live DB data with simulation fallback
  const enrichedIntersections: EnrichedIntersection[] = useMemo(() => {
    return intersections.map((item, idx) => {
      const live = liveTraffic[item.nodeId];
      const node = nodes[idx] || null;

      let status: "Red" | "Yellow" | "Green";
      let p: number;

      if (live) {
        // Real DB data takes priority
        status = live.status as "Red" | "Yellow" | "Green";
        p = live.congestionLevel;
      } else if (node) {
        // Use simulated network-status data
        const laneDensities = Object.values(node.lanes).map(l => l.density);
        const avgDensity = laneDensities.reduce((a, b) => a + b, 0) / (laneDensities.length || 1);
        p = avgDensity / 100;
        status = avgDensity > 70 ? "Red" : avgDensity > 40 ? "Yellow" : "Green";
      } else {
        // Final deterministic fallback
        const seed = parseInt(item.nodeId.slice(-3)) || 100;
        status = (seed % 10 < 2) ? "Red" : (seed % 10 < 5) ? "Yellow" : "Green";
        p = status === "Red" ? 0.78 : status === "Yellow" ? 0.48 : 0.15;
      }

      return { ...item, status, p };
    });
  }, [nodes, liveTraffic]);

  // Merge simulated devices with live DB devices (re-generates every 8s tick)
  const devices: DeviceStatus[] = useMemo(() => {
    const simulated = generateDevicesForIntersections(tick);
    if (liveDevices.length === 0) return simulated;

    // Merge: live devices override simulated ones by ID
    const liveMap = new Map(liveDevices.map(d => [d.id, d]));
    return simulated.map(dev => {
      const live = liveMap.get(dev.id);
      if (live) {
        return { ...dev, status: live.status, firmware: live.firmware, issues: live.issues, lastPing: live.lastPing, uptime: live.uptime };
      }
      return dev;
    });
  }, [liveDevices, tick]);

  const vulnerabilities: VulnerabilityData[] = useMemo(() => {
    return generateVulnerabilities(devices);
  }, [devices]);

  return { nodes, intersections: enrichedIntersections, liveTraffic, devices, vulnerabilities };
}
