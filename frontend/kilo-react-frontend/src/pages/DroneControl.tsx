import React, { useState, useEffect } from "react";

interface DroneStatus {
  connected: boolean;
  battery: number;
  altitude: number;
  gps: { lat: number; lon: number } | null;
  mode: string;
}

export default function DroneControl() {
  const [status, setStatus] = useState<DroneStatus>({
    connected: false,
    battery: 0,
    altitude: 0,
    gps: null,
    mode: "IDLE"
  });

  useEffect(() => {
    fetchDroneStatus();
    const interval = setInterval(fetchDroneStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchDroneStatus = async () => {
    try {
      const res = await fetch("/api/drone/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch drone status:", err);
    }
  };

  const sendCommand = async (command: string) => {
    try {
      await fetch("/api/drone/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command })
      });
    } catch (err) {
      console.error("Failed to send command:", err);
    }
  };

  return (
    <div className="p-6 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-neon mb-8 font-mono uppercase tracking-wider">
          🚁 Drone Control
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Connection</div>
            <div className={"text-2xl font-bold " + (status.connected ? "text-neon" : "text-red-500")}>
              {status.connected ? "ONLINE" : "OFFLINE"}
            </div>
          </div>

          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Battery</div>
            <div className="text-2xl font-bold text-neon">{status.battery}%</div>
          </div>

          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Altitude</div>
            <div className="text-2xl font-bold text-neon">{status.altitude.toFixed(1)}m</div>
          </div>

          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Mode</div>
            <div className="text-2xl font-bold text-neon">{status.mode}</div>
          </div>
        </div>

        {status.gps && (
          <div className="bg-black border-2 border-neon-dim p-6 rounded mb-8">
            <h3 className="text-xl font-bold text-neon mb-4">GPS Position</h3>
            <div className="grid grid-cols-2 gap-4 font-mono">
              <div>
                <span className="text-gray-400">Latitude:</span>
                <span className="text-neon ml-4">{status.gps.lat.toFixed(6)}</span>
              </div>
              <div>
                <span className="text-gray-400">Longitude:</span>
                <span className="text-neon ml-4">{status.gps.lon.toFixed(6)}</span>
              </div>
            </div>
          </div>
        )}

        <div className="bg-black border-2 border-neon p-6 rounded">
          <h3 className="text-xl font-bold text-neon mb-6">Commands</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              onClick={() => sendCommand("ARM")}
              className="bg-neon text-black px-6 py-4 rounded font-bold hover:bg-white transition-colors uppercase"
              disabled={!status.connected}
            >
              ARM
            </button>
            <button
              onClick={() => sendCommand("DISARM")}
              className="bg-red-600 text-white px-6 py-4 rounded font-bold hover:bg-red-700 transition-colors uppercase"
              disabled={!status.connected}
            >
              DISARM
            </button>
            <button
              onClick={() => sendCommand("TAKEOFF")}
              className="bg-neon text-black px-6 py-4 rounded font-bold hover:bg-white transition-colors uppercase"
              disabled={!status.connected}
            >
              TAKEOFF
            </button>
            <button
              onClick={() => sendCommand("LAND")}
              className="bg-yellow-600 text-black px-6 py-4 rounded font-bold hover:bg-yellow-500 transition-colors uppercase"
              disabled={!status.connected}
            >
              LAND
            </button>
            <button
              onClick={() => sendCommand("RTL")}
              className="bg-blue-600 text-white px-6 py-4 rounded font-bold hover:bg-blue-700 transition-colors uppercase"
              disabled={!status.connected}
            >
              RETURN HOME
            </button>
            <button
              onClick={() => sendCommand("EMERGENCY")}
              className="bg-red-600 text-white px-6 py-4 rounded font-bold hover:bg-red-700 transition-colors uppercase border-2 border-red-400"
              disabled={!status.connected}
            >
              EMERGENCY
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
