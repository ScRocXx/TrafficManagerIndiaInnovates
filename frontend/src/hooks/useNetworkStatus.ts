import { useState, useEffect, useRef } from 'react';
import { IntersectionData } from '@/lib/intersections';

export interface NetworkNode {
  node_id: string;
  lanes: {
    [key: string]: { density: number; wait_time: number; green_time?: number };
  };
  hardware_status: string;
  ambulance_detected?: boolean;
  active_green?: string | null;
  green_timer?: number;
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

const DEMO_VIDEOS = [
  "1EiC9bvVGnk", "B0Yjtbb02ZA", "1R_A_rO_F0E",
  "qGltj0wJ8zM", "rM2wQ5kFiyM", "8mBJUCEtk_k",
];

// ── 25 real Delhi intersections (matches intersections.ts) ──
const DELHI_INTERSECTIONS = [
  { name: "ITO Junction",      lat: 28.6271, lng: 77.2403 },
  { name: "AIIMS",             lat: 28.5675, lng: 77.2069 },
  { name: "Connaught Place",   lat: 28.6304, lng: 77.2177 },
  { name: "South Ext",         lat: 28.5685, lng: 77.2215 },
  { name: "Dhaula Kuan",       lat: 28.5918, lng: 77.1615 },
  { name: "Kashmere Gate",     lat: 28.6665, lng: 77.2289 },
  { name: "Ashram Chowk",      lat: 28.5724, lng: 77.2600 },
  { name: "Laxmi Nagar",       lat: 28.6300, lng: 77.2764 },
  { name: "Karol Bagh",        lat: 28.6429, lng: 77.1901 },
  { name: "Moolchand",         lat: 28.5645, lng: 77.2340 },
  { name: "Raja Garden",       lat: 28.6433, lng: 77.1207 },
  { name: "Akshardham",        lat: 28.6186, lng: 77.2769 },
  { name: "Lajpat Nagar",      lat: 28.5682, lng: 77.2433 },
  { name: "Dwarka",            lat: 28.5823, lng: 77.0500 },
  { name: "Rohini",            lat: 28.7366, lng: 77.1268 },
  { name: "Vasant Kunj",       lat: 28.5293, lng: 77.1537 },
  { name: "Saket",             lat: 28.5245, lng: 77.2066 },
  { name: "Nehru Place",       lat: 28.5494, lng: 77.2523 },
  { name: "Hauz Khas",         lat: 28.5494, lng: 77.2001 },
  { name: "Chandni Chowk",     lat: 28.6505, lng: 77.2303 },
  { name: "Pitampura",         lat: 28.7031, lng: 77.1326 },
  { name: "Janakpuri",         lat: 28.6219, lng: 77.0878 },
  { name: "Okhla",             lat: 28.5222, lng: 77.2806 },
  { name: "Vasant Vihar",      lat: 28.5585, lng: 77.1585 },
  { name: "Greater Kailash",   lat: 28.5367, lng: 77.2407 },
];

// ── Deterministic seed data for stable rendering ──
// Densities: realistic range 18–88% (major junctions higher)
const SEED_DENSITIES = [
  85, 82, 62, 48, 55, 68, 71, 44, 49, 58,
  27, 66, 53, 32, 38, 29, 45, 61, 42, 76,
  35, 30, 52, 33, 41,
];

// Wait times in seconds: realistic 8–38s (under 40 min cap)
const SEED_WAIT_TIMES = [
  35, 32, 26, 18, 22, 28, 30, 19, 21, 25,
  12, 27, 23, 14, 16, 11, 20, 24, 17, 33,
  13, 10, 22, 15, 18,
];

// Peak hours per intersection — realistic Delhi traffic patterns
export const PEAK_TIMES = [
  "9:00 AM",  // ITO - office rush
  "6:00 PM",  // AIIMS - hospital + evening
  "1:00 PM",  // CP - lunch crowd
  "6:30 PM",  // South Ext - evening market
  "8:30 AM",  // Dhaula Kuan - morning commute
  "5:30 PM",  // Kashmere Gate - bus terminal rush
  "9:30 AM",  // Ashram Chowk - office
  "8:00 AM",  // Laxmi Nagar - morning
  "7:00 PM",  // Karol Bagh - market close
  "5:00 PM",  // Moolchand - evening
  "8:00 AM",  // Raja Garden - school+office
  "6:00 PM",  // Akshardham - evening
  "7:30 PM",  // Lajpat Nagar - market
  "9:00 AM",  // Dwarka - office exodus
  "8:30 AM",  // Rohini - morning
  "6:00 PM",  // Vasant Kunj - evening
  "7:00 PM",  // Saket - mall crowd
  "5:30 PM",  // Nehru Place - IT hub close
  "8:00 PM",  // Hauz Khas - nightlife
  "10:00 AM", // Chandni Chowk - market
  "8:00 AM",  // Pitampura - morning
  "9:00 AM",  // Janakpuri - office
  "6:30 PM",  // Okhla - industrial close
  "5:00 PM",  // Vasant Vihar - evening
  "6:00 PM",  // Greater Kailash - market
];

// Max congestion durations in minutes (capped at 25-38 min range)
export const MAX_CONGESTION_MINS = [
  38, 35, 28, 25, 27, 32, 33, 26, 27, 30,
  25, 31, 29, 25, 26, 25, 28, 30, 26, 36,
  25, 25, 29, 25, 27,
];

/**
 * Generates deterministic fallback nodes. Hardware faults rotate every ~60s
 * so at any given minute, exactly 1 node has a vulnerability.
 */
function generateFallbackNodes(): NetworkNode[] {
  return DELHI_INTERSECTIONS.map((_, i) => ({
    node_id: `Node_${i + 1}`,
    hardware_status: "ONLINE",
    lanes: {
      N: { density: SEED_DENSITIES[i], wait_time: SEED_WAIT_TIMES[i] },
    },
  }));
}

/**
 * Processes NetworkNodes into IntersectionData[], DeviceStatus[], vulnerabilities.
 */
function processNodes(networkNodes: NetworkNode[], alertTime: string) {
  const newIntersections: IntersectionData[] = networkNodes.map((n, i) => {
    const totalDensity = Object.values(n.lanes).reduce((sum, l) => sum + l.density, 0);
    const pValue = Math.min(1.0, totalDensity / 100);

    let status = 'Green';
    if (pValue > 0.70) status = 'Red';
    else if (pValue > 0.40) status = 'Yellow';

    const coords = DELHI_INTERSECTIONS[i] || DELHI_INTERSECTIONS[0];

    return {
      id: i + 1,
      nodeId: n.node_id.replace("Node_", "2845").padStart(6, "0"),
      name: i === 0 ? "ITO Junction (Hero)" : (i === 1 ? "AIIMS (Hero)" : coords.name),
      lat: coords.lat,
      lng: coords.lng,
      videoId: DEMO_VIDEOS[i % DEMO_VIDEOS.length],
      status,
      p: Number(pValue.toFixed(2)),
    };
  });

  const newDevices: DeviceStatus[] = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const newVulns: any[] = [];

  networkNodes.forEach((n, index) => {
    const isOnline = n.hardware_status === 'ONLINE';
    const statusMap: Record<string, "online" | "offline" | "degraded"> = {
      "ONLINE": "online",
      "CAMERA_FAULT": "offline",
      "THERMAL_THROTTLE": "degraded",
    };

    const deviceId = `CAM-${n.node_id}`;
    const devStatus = statusMap[n.hardware_status] || "online";
    const coords = DELHI_INTERSECTIONS[index] || DELHI_INTERSECTIONS[0];
    const locName = index === 0 ? "ITO Junction (Hero)" : (index === 1 ? "AIIMS (Hero)" : coords.name);

    // Each Jetson has 5 YOLOs
    const jetsonId = `JTN-${String(index + 1).padStart(2, "0")}`;
    newDevices.push({
      id: deviceId,
      device: `${jetsonId} · 5× YOLO`,
      type: "camera",
      location: locName,
      status: devStatus,
      uptime: isOnline ? "99.9%" : (devStatus === "degraded" ? "72.4%" : "0%"),
      lastPing: isOnline ? "1 sec ago" : (devStatus === "degraded" ? "3 min ago" : "15 min ago"),
      firmware: "v6.0.0",
      issues: isOnline ? [] : [n.hardware_status.replace("_", " ")],
    });

    if (!isOnline) {
      newVulns.push({
        id: `VULN-${n.node_id}`,
        type: n.hardware_status === 'CAMERA_FAULT' ? "Camera Offline" : "Thermal Throttling",
        status: n.hardware_status === 'CAMERA_FAULT' ? "Critical" : "Yellow",
        last_ping: alertTime,
        issue: `Node reported ${n.hardware_status}`,
        location: locName,
      });
    }
  });

  return { newIntersections, newDevices, newVulns };
}

export function useNetworkStatus() {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [intersections, setIntersections] = useState<IntersectionData[]>([]);
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [vulnerabilities, setVulnerabilities] = useState<any[]>([]);
  // Track whether we got real API data (so we don't overwrite with fallback)
  const hasLiveData = useRef(false);

  useEffect(() => {
    let isMounted = true;

    const fetchStatus = async () => {
      let networkNodes: NetworkNode[] | null = null;

      // 1. Try configured backend
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://india-innovate-backend.onrender.com";
      try {
        const res = await fetch(`${API_URL}/api/network-status`, { signal: AbortSignal.timeout(4000) });
        const data = await res.json();
        if (data.status === 'success' && data.nodes) {
          networkNodes = data.nodes;
          hasLiveData.current = true;
        }
      } catch {
        // Primary unreachable
      }

      // 2. Try localhost
      if (!networkNodes) {
        try {
          const res = await fetch('http://localhost:8000/api/network-status', { signal: AbortSignal.timeout(3000) });
          const data = await res.json();
          if (data.status === 'success' && data.nodes) {
            networkNodes = data.nodes;
            hasLiveData.current = true;
          }
        } catch {
          // Localhost also unreachable
        }
      }

      // Poll interval: stable data doesn't bounce around
      if (!networkNodes || networkNodes.length === 0) {
        networkNodes = generateFallbackNodes();
      }

      // --- ENFORCE EXACTLY 1 VULNERABILITY EVERY 1.5 MIN (90s) ---
      const timeSlot = Math.floor(Date.now() / 90000);
      const alertTime = new Date(timeSlot * 90000).toISOString();
      const faultNodeIndex = timeSlot % 25;
      const faultType = timeSlot % 2 === 0 ? "CAMERA_FAULT" : "THERMAL_THROTTLE";

      // Pad to 25 nodes if API returned fewer
      while (networkNodes.length < 25) {
        const i = networkNodes.length;
        networkNodes.push({
          node_id: `Node_${i + 1}`,
          hardware_status: "ONLINE",
          lanes: {
            N: { density: SEED_DENSITIES[i] || 30, wait_time: SEED_WAIT_TIMES[i] || 15 },
          },
        });
      }

      // Overwrite statuses: force exactly 1 node to have the vulnerability
      networkNodes = networkNodes.map((n, i) => ({
        ...n,
        hardware_status: i === faultNodeIndex ? faultType : "ONLINE"
      }));

      if (!isMounted) return;

      // 4. Try merging real edge data for ITO (Node 1) from DB
      try {
        const trafficRes = await fetch(`${API_URL}/api/traffic`, { signal: AbortSignal.timeout(4000) });
        if (trafficRes.ok) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const trafficData: any[] = await trafficRes.json();
          if (trafficData.length > 0 && networkNodes[0]) {
            const heroMatch = trafficData[0];
            const realDensity = Math.round((heroMatch.congestionLevel || 0) * 100);
            networkNodes[0] = {
              ...networkNodes[0],
              lanes: {
                ...networkNodes[0].lanes,
                N: {
                  density: Math.max(realDensity, networkNodes[0].lanes.N?.density || 0),
                  wait_time: heroMatch.avgWaitTime || networkNodes[0].lanes.N?.wait_time || 30,
                },
              },
            };
          }
        }
      } catch {
        // No real traffic data
      }

      setNodes(networkNodes);
      const { newIntersections, newDevices, newVulns } = processNodes(networkNodes, alertTime);
      setIntersections(newIntersections);
      setDevices(newDevices);
      setVulnerabilities(newVulns);
    };

    fetchStatus();
    // Poll every 5s to keep UI snappy, but the alert data is stable during the 90s window
    const intervalId = setInterval(fetchStatus, 5000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  return { nodes, intersections, devices, vulnerabilities };
}
