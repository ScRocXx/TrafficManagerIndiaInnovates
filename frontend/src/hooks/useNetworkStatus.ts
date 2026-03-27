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

/* ── Hook ── */
export function useNetworkStatus() {
  const [nodes, setNodes] = useState<(NodeData | null)[]>([]);
  const [liveTraffic, setLiveTraffic] = useState<Record<string, { status: string; congestionLevel: number; vehiclesPassed: number }>>({});

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

  return { nodes, intersections: enrichedIntersections, liveTraffic };
}
