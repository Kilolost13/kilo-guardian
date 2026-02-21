import React, { useState, useEffect } from "react";

interface NetworkDevice {
  ip: string;
  mac: string;
  hostname: string;
  vendor: string;
  status: "online" | "offline";
  lastSeen: string;
}

interface NetworkStats {
  totalDevices: number;
  onlineDevices: number;
  bandwidth: { download: number; upload: number };
  threats: number;
}

export default function NetworkControl() {
  const [devices, setDevices] = useState<NetworkDevice[]>([]);
  const [stats, setStats] = useState<NetworkStats>({
    totalDevices: 0,
    onlineDevices: 0,
    bandwidth: { download: 0, upload: 0 },
    threats: 0
  });
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    fetchDevices();
    fetchStats();
    const interval = setInterval(() => {
      fetchDevices();
      fetchStats();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchDevices = async () => {
    try {
      const res = await fetch("/api/network/devices");
      if (res.ok) {
        const data = await res.json();
        setDevices(data.devices || []);
      }
    } catch (err) {
      console.error("Failed to fetch devices:", err);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch("/api/network/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  };

  const startScan = async () => {
    setScanning(true);
    try {
      await fetch("/api/network/scan", { method: "POST" });
      setTimeout(() => {
        fetchDevices();
        setScanning(false);
      }, 5000);
    } catch (err) {
      console.error("Failed to start scan:", err);
      setScanning(false);
    }
  };

  const blockDevice = async (ip: string) => {
    try {
      await fetch("/api/network/block", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip })
      });
      fetchDevices();
    } catch (err) {
      console.error("Failed to block device:", err);
    }
  };

  return (
    <div className="p-6 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-neon mb-8 font-mono uppercase tracking-wider">
          🌐 Network Control
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Total Devices</div>
            <div className="text-3xl font-bold text-neon">{stats.totalDevices}</div>
          </div>

          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Online</div>
            <div className="text-3xl font-bold text-green-500">{stats.onlineDevices}</div>
          </div>

          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Download</div>
            <div className="text-3xl font-bold text-neon">{stats.bandwidth.download.toFixed(1)} MB/s</div>
          </div>

          <div className="bg-black border-2 border-neon-dim p-6 rounded">
            <div className="text-gray-400 text-sm mb-2">Threats Blocked</div>
            <div className="text-3xl font-bold text-red-500">{stats.threats}</div>
          </div>
        </div>

        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-neon">Connected Devices</h2>
          <button
            onClick={startScan}
            disabled={scanning}
            className="bg-neon text-black px-6 py-2 rounded font-bold hover:bg-white transition-colors uppercase disabled:opacity-50"
          >
            {scanning ? "SCANNING..." : "SCAN NETWORK"}
          </button>
        </div>

        <div className="bg-black border-2 border-neon p-6 rounded">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-neon-dim">
                  <th className="text-left py-3 px-4 text-neon font-mono">IP Address</th>
                  <th className="text-left py-3 px-4 text-neon font-mono">Hostname</th>
                  <th className="text-left py-3 px-4 text-neon font-mono">MAC Address</th>
                  <th className="text-left py-3 px-4 text-neon font-mono">Vendor</th>
                  <th className="text-left py-3 px-4 text-neon font-mono">Status</th>
                  <th className="text-left py-3 px-4 text-neon font-mono">Actions</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((device) => (
                  <tr key={device.ip} className="border-b border-gray-800 hover:bg-gray-900">
                    <td className="py-3 px-4 text-white font-mono">{device.ip}</td>
                    <td className="py-3 px-4 text-white">{device.hostname || "-"}</td>
                    <td className="py-3 px-4 text-gray-400 font-mono text-sm">{device.mac}</td>
                    <td className="py-3 px-4 text-gray-400">{device.vendor || "Unknown"}</td>
                    <td className="py-3 px-4">
                      <span className={"px-3 py-1 rounded text-xs font-bold " + (device.status === "online" ? "bg-green-500 text-black" : "bg-gray-600 text-white")}>
                        {device.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => blockDevice(device.ip)}
                        className="bg-red-600 text-white px-4 py-1 rounded text-sm hover:bg-red-700 transition-colors"
                      >
                        BLOCK
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {devices.length === 0 && (
              <div className="text-gray-500 text-center py-12">No devices detected. Click SCAN NETWORK to discover devices.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
