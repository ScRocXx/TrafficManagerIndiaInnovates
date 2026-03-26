export interface IntersectionData {
  id: number;
  nodeId: string;
  name: string;
  lat: number;
  lng: number;
  status: string;
  p: number;
  videoId: string;
}

const DEMO_VIDEOS = [
  "1EiC9bvVGnk", // Jackson Hole Town Square
  "B0Yjtbb02ZA", // Live Traffic
  "1R_A_rO_F0E", // Vegas
  "qGltj0wJ8zM", // Shibuya
  "rM2wQ5kFiyM", // Highway
  "8mBJUCEtk_k", // London
];

export const intersections: IntersectionData[] = [
  { id: 1, nodeId: "284501", name: "ITO Junction", lat: 28.6271, lng: 77.2403, status: "Red", p: 0.85, videoId: DEMO_VIDEOS[0] },
  { id: 2, nodeId: "284502", name: "AIIMS", lat: 28.5675, lng: 77.2069, status: "Red", p: 0.92, videoId: DEMO_VIDEOS[1] },
  { id: 3, nodeId: "284503", name: "Connaught Place", lat: 28.6304, lng: 77.2177, status: "Yellow", p: 0.60, videoId: DEMO_VIDEOS[2] },
  { id: 4, nodeId: "284504", name: "South Ext", lat: 28.5685, lng: 77.2215, status: "Red", p: 0.75, videoId: DEMO_VIDEOS[3] },
  { id: 5, nodeId: "284505", name: "Dhaula Kuan", lat: 28.5918, lng: 77.1615, status: "Green", p: 0.25, videoId: DEMO_VIDEOS[4] },
  { id: 6, nodeId: "284506", name: "Kashmere Gate", lat: 28.6665, lng: 77.2289, status: "Yellow", p: 0.55, videoId: DEMO_VIDEOS[5] },
  { id: 7, nodeId: "284507", name: "Ashram Chowk", lat: 28.5724, lng: 77.2600, status: "Red", p: 0.88, videoId: DEMO_VIDEOS[0] },
  { id: 8, nodeId: "284508", name: "Laxmi Nagar", lat: 28.6300, lng: 77.2764, status: "Green", p: 0.30, videoId: DEMO_VIDEOS[1] },
  { id: 9, nodeId: "284509", name: "Karol Bagh", lat: 28.6429, lng: 77.1901, status: "Yellow", p: 0.45, videoId: DEMO_VIDEOS[2] },
  { id: 10, nodeId: "284510", name: "Moolchand", lat: 28.5645, lng: 77.2340, status: "Green", p: 0.20, videoId: DEMO_VIDEOS[3] },
  { id: 11, nodeId: "284511", name: "Raja Garden", lat: 28.6433, lng: 77.1207, status: "Red", p: 0.78, videoId: DEMO_VIDEOS[4] },
  { id: 12, nodeId: "284512", name: "Akshardham", lat: 28.6186, lng: 77.2769, status: "Green", p: 0.15, videoId: DEMO_VIDEOS[5] },
  { id: 13, nodeId: "284513", name: "Lajpat Nagar", lat: 28.5682, lng: 77.2433, status: "Yellow", p: 0.58, videoId: DEMO_VIDEOS[0] },
  { id: 14, nodeId: "284514", name: "Dwarka", lat: 28.5823, lng: 77.0500, status: "Green", p: 0.22, videoId: DEMO_VIDEOS[1] },
  { id: 15, nodeId: "284515", name: "Rohini", lat: 28.7366, lng: 77.1268, status: "Red", p: 0.82, videoId: DEMO_VIDEOS[2] },
  { id: 16, nodeId: "284516", name: "Vasant Kunj", lat: 28.5293, lng: 77.1537, status: "Green", p: 0.35, videoId: DEMO_VIDEOS[3] },
  { id: 17, nodeId: "284517", name: "Saket", lat: 28.5245, lng: 77.2066, status: "Yellow", p: 0.65, videoId: DEMO_VIDEOS[4] },
  { id: 18, nodeId: "284518", name: "Nehru Place", lat: 28.5494, lng: 77.2523, status: "Red", p: 0.95, videoId: DEMO_VIDEOS[5] },
  { id: 19, nodeId: "284519", name: "Hauz Khas", lat: 28.5494, lng: 77.2001, status: "Green", p: 0.12, videoId: DEMO_VIDEOS[0] },
  { id: 20, nodeId: "284520", name: "Chandni Chowk", lat: 28.6505, lng: 77.2303, status: "Red", p: 0.98, videoId: DEMO_VIDEOS[1] },
  { id: 21, nodeId: "284521", name: "Pitampura", lat: 28.7031, lng: 77.1326, status: "Yellow", p: 0.48, videoId: DEMO_VIDEOS[2] },
  { id: 22, nodeId: "284522", name: "Janakpuri", lat: 28.6219, lng: 77.0878, status: "Green", p: 0.28, videoId: DEMO_VIDEOS[3] },
  { id: 23, nodeId: "284523", name: "Okhla", lat: 28.5222, lng: 77.2806, status: "Red", p: 0.81, videoId: DEMO_VIDEOS[4] },
  { id: 24, nodeId: "284524", name: "Vasant Vihar", lat: 28.5585, lng: 77.1585, status: "Yellow", p: 0.51, videoId: DEMO_VIDEOS[5] },
  { id: 25, nodeId: "284525", name: "Greater Kailash", lat: 28.5367, lng: 77.2407, status: "Green", p: 0.18, videoId: DEMO_VIDEOS[0] }
];
