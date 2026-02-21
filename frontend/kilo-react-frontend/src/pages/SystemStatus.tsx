import React, { useState, useEffect } from 'react';
import { Card } from '../components/shared/Card';
import { agentApi } from '../services/api';

interface ServiceEntry {
  layer: string;
  url: string;
  port: number;
  healthy: boolean;
  capabilities: string[];
  last_checked: number;
}

interface AlertEntry {
  type?: string;
  content?: string;
  priority?: string;
  severity?: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

const SystemStatus: React.FC = () => {
  const [services, setServices] = useState<Record<string, ServiceEntry>>({});
  const [alerts, setAlerts] = useState<AlertEntry[]>([]);
  const [agentOnline, setAgentOnline] = useState<boolean | null>(null);
  const [lastRefresh, setLastRefresh] = useState('');

  const refresh = async () => {
    // Agent health
    try {
      const h = await agentApi.get('/health');
      setAgentOnline(h.status === 200);
    } catch {
      setAgentOnline(false);
    }

    // Full service registry
    try {
      const res = await agentApi.get('/services');
      setServices(res.data);
    } catch { /* agent unreachable */ }

    // Active alerts
    try {
      const res = await agentApi.get('/monitoring/alerts');
      setAlerts(res.data?.alerts || []);
    } catch { /* no alerts endpoint */ }

    setLastRefresh(new Date().toLocaleTimeString());
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, []);

  // Partition services by layer
  const k3sServices = Object.entries(services).filter(([, s]) => s.layer === 'k3s');
  const guardianServices = Object.entries(services).filter(([, s]) => s.layer === 'guardian');

  const healthyCount = k3sServices.filter(([, s]) => s.healthy).length;
  const totalK3s = k3sServices.length;

  return (
    <div className="min-h-screen p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="font-header text-2xl text-zombie-green neon-text">⚙️ SYSTEM STATUS</h1>
        <div className="flex items-center gap-3">
          <button onClick={refresh} className="text-xs font-header px-3 py-1 border border-zombie-green/40 rounded text-zombie-green hover:bg-dark-card transition-all">
            ↻ REFRESH
          </button>
          {lastRefresh && <span className="text-xs text-zombie-green/40">Updated: {lastRefresh}</span>}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <Card className="glass-panel text-center">
          <div className={`text-xs font-header mb-1 ${agentOnline ? 'glow-green' : agentOnline === false ? 'glow-red' : 'glow-yellow'}`}>
            UNIFIED AGENT
          </div>
          <div className={`text-xl font-header ${agentOnline ? 'glow-green' : agentOnline === false ? 'glow-red' : 'glow-yellow'}`}>
            {agentOnline === null ? '…' : agentOnline ? 'ONLINE' : 'OFFLINE'}
          </div>
        </Card>
        <Card className="glass-panel text-center">
          <div className="text-xs font-header text-zombie-green/50 mb-1">K3S PODS</div>
          <div className="text-xl font-header text-zombie-green neon-text">{healthyCount}<span className="text-zombie-green/40 text-sm">/{totalK3s}</span></div>
          <div className="text-xs text-zombie-green/40">healthy</div>
        </Card>
        <Card className="glass-panel text-center">
          <div className={`text-xs font-header mb-1 ${alerts.length > 0 ? 'glow-red' : 'glow-green'}`}>
            ALERTS
          </div>
          <div className={`text-xl font-header ${alerts.length > 0 ? 'glow-red' : 'glow-green'}`}>
            {alerts.length}
          </div>
        </Card>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card className="mb-4 glass-panel border-red-900/60">
          <h2 className="font-header text-sm glow-red mb-2">⚠️ ACTIVE ALERTS</h2>
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-start gap-2 border border-red-900/40 rounded p-2">
                <span className="text-red-400 text-lg">⚠</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-red-300">{a.content || a.severity || 'Unknown alert'}</p>
                  {a.timestamp && <p className="text-xs text-zombie-green/40 mt-0.5">{a.timestamp}</p>}
                </div>
                <span className={`text-xs font-header px-2 py-0.5 rounded ${a.priority === 'high' ? 'bg-red-900 text-red-300' : 'bg-dark-card text-zombie-green/60'}`}>
                  {a.priority || 'normal'}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* K3s microservices grid */}
      <Card className="mb-4 glass-panel">
        <h2 className="font-header text-sm text-zombie-green mb-3 neon-text">K3S MICROSERVICES</h2>
        <div className="grid grid-cols-2 gap-2">
          {k3sServices.map(([name, svc]) => (
            <div key={name} className={`flex items-center gap-2 p-2 rounded border ${svc.healthy ? 'border-zombie-green/30 bg-dark-card' : 'border-red-900/50 bg-red-950/30'}`}>
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${svc.healthy ? 'bg-zombie-green shadow-lg shadow-zombie-green/50' : 'bg-red-500 animate-pulse'}`} />
              <div className="min-w-0 flex-1">
                <div className="text-xs font-header text-zombie-green truncate capitalize">{name.replace(/_/g, ' ')}</div>
                <div className="text-xs text-zombie-green/40">:{svc.port}</div>
              </div>
              <span className={`text-xs font-header ${svc.healthy ? 'text-zombie-green' : 'text-red-400'}`}>
                {svc.healthy ? '✓' : '✗'}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* Guardian capabilities */}
      <Card className="glass-panel">
        <h2 className="font-header text-sm text-zombie-green mb-3 neon-text">GUARDIAN CAPABILITIES</h2>
        <div className="grid grid-cols-2 gap-2">
          {guardianServices.map(([name, svc]) => (
            <div key={name} className="flex items-center gap-2 p-2 rounded border border-zombie-green/20 bg-dark-card">
              <span className="w-2 h-2 rounded-full bg-neon-blue flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs font-header text-zombie-green truncate capitalize">{name.replace(/_/g, ' ')}</div>
                <div className="text-xs text-zombie-green/40 truncate">{svc.capabilities.slice(0, 3).join(', ')}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default SystemStatus;
