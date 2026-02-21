import React, { useState, useEffect } from 'react';
import { Card } from '../components/shared/Card';
import api from '../services/api';

interface ActivityResult {
  primary_activity: string;
  confidence: number;
  all_scores?: Record<string, number>;
  detected_objects?: string[];
  posture?: string;
  object_count?: number;
}

const CameraMonitor: React.FC = () => {
  const [activity, setActivity] = useState<ActivityResult | null>(null);
  const [camHealth, setCamHealth] = useState<'online' | 'offline' | 'checking'>('checking');
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await api.get('/cam/health');
        setCamHealth(res.status === 200 ? 'online' : 'offline');
      } catch {
        setCamHealth('offline');
      }
    };
    check();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const poll = async () => {
      try {
        const res = await api.get('/cam/activity');
        if (res.data) {
          setActivity(res.data as ActivityResult);
          setLastUpdate(new Date().toLocaleTimeString());
        }
      } catch { /* cam may not have data yet */ }
    };
    poll();
    const interval = setInterval(poll, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const statusColor = camHealth === 'online' ? 'glow-green' : camHealth === 'offline' ? 'glow-red' : 'glow-yellow';
  const statusLabel = camHealth === 'online' ? 'ONLINE' : camHealth === 'offline' ? 'OFFLINE' : 'CHECKING…';

  return (
    <div className="min-h-screen p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="font-header text-2xl text-zombie-green neon-text">📷 CAMERA MONITOR</h1>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-header ${statusColor}`}>● {statusLabel}</span>
          <label className="flex items-center gap-2 text-xs text-zombie-green cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} className="accent-zombie-green" />
            AUTO-REFRESH
          </label>
        </div>
      </div>

      {/* Live feed */}
      <Card className="mb-4 glass-panel">
        <h2 className="font-header text-sm text-zombie-green mb-3 neon-text">LIVE FEED</h2>
        <div className="rounded-lg border border-zombie-green/30 overflow-hidden bg-dark-bg flex items-center justify-center" style={{ minHeight: 220 }}>
          {camHealth === 'online' ? (
            <img src="/api/cam/stream" alt="Live camera feed" className="w-full max-h-[320px] object-contain" onError={() => setCamHealth('offline')} />
          ) : (
            <div className="text-zombie-green/50 text-center py-12">
              <div className="text-4xl mb-2">📷</div>
              <p className="text-sm font-header">Camera stream {camHealth === 'offline' ? 'unavailable' : 'loading…'}</p>
              <p className="text-xs text-zombie-green/40 mt-1">No /dev/video0 device detected</p>
            </div>
          )}
        </div>
      </Card>

      {/* Activity detection results */}
      <Card className="mb-4 glass-panel">
        <div className="flex justify-between items-center mb-3">
          <h2 className="font-header text-sm text-zombie-green neon-text">ACTIVITY DETECTION</h2>
          {lastUpdate && <span className="text-xs text-zombie-green/50">Updated: {lastUpdate}</span>}
        </div>
        {activity ? (
          <div className="space-y-3">
            {/* Primary activity callout */}
            <div className="neon-border rounded-lg p-4 text-center">
              <div className="text-3xl font-header text-zombie-green neon-text capitalize">{activity.primary_activity}</div>
              <div className="text-sm text-zombie-green/70 mt-1">
                Confidence: <span className="text-zombie-green font-bold">{(activity.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>

            {/* Posture / object count */}
            <div className="grid grid-cols-2 gap-3">
              {activity.posture && (
                <div className="glass-panel rounded-lg p-3">
                  <div className="text-xs text-zombie-green/50 font-header mb-1">POSTURE</div>
                  <div className="text-sm text-zombie-green capitalize">{activity.posture}</div>
                </div>
              )}
              {activity.object_count !== undefined && (
                <div className="glass-panel rounded-lg p-3">
                  <div className="text-xs text-zombie-green/50 font-header mb-1">OBJECTS</div>
                  <div className="text-sm text-zombie-green">{activity.object_count}</div>
                </div>
              )}
            </div>

            {/* Detected objects tags */}
            {activity.detected_objects && activity.detected_objects.length > 0 && (
              <div className="glass-panel rounded-lg p-3">
                <div className="text-xs text-zombie-green/50 font-header mb-2">DETECTED OBJECTS</div>
                <div className="flex flex-wrap gap-2">
                  {activity.detected_objects.map((obj, i) => (
                    <span key={i} className="text-xs px-2 py-1 border border-zombie-green/40 rounded text-zombie-green">{obj}</span>
                  ))}
                </div>
              </div>
            )}

            {/* All scores bar chart */}
            {activity.all_scores && (
              <div className="glass-panel rounded-lg p-3">
                <div className="text-xs text-zombie-green/50 font-header mb-2">ALL SCORES</div>
                <div className="space-y-2">
                  {Object.entries(activity.all_scores).sort((a, b) => b[1] - a[1]).map(([label, score]) => {
                    const pct = score * 100;
                    const barColor = score > 0.7 ? '#39FF14' : score > 0.4 ? '#FFFF00' : '#666';
                    return (
                      <div key={label} className="flex items-center gap-2">
                        <span className="text-xs text-zombie-green/70 w-24 capitalize">{label}</span>
                        <div className="flex-1 bg-dark-card rounded-full h-2">
                          <div className="h-2 rounded-full" style={{ width: `${pct}%`, background: barColor }} />
                        </div>
                        <span className="text-xs text-zombie-green/50 w-12 text-right">{pct.toFixed(0)}%</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center text-zombie-green/40 py-8">
            <p className="text-sm">No activity data available</p>
            <p className="text-xs mt-1">Waiting for camera detection…</p>
          </div>
        )}
      </Card>
    </div>
  );
};

export default CameraMonitor;
