import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/shared/Card';
import { Button } from '../components/shared/Button';
import api from '../services/api';

/* ═══════════════════════════════════════════════════════════════════════════
 * INTERFACES
 * ═══════════════════════════════════════════════════════════════════════════ */
interface PluginEntry { name: string; url: string; version: string; keywords: string[]; description: string; registered_at: string; status: string; }
interface ServiceDetail { ok: boolean; checked_at: string; message: Record<string, any>; }
interface PodInfo { name: string; status: string; restarts: number; age: string; node: string; ready: string; }
interface NodeInfo { name: string; status: string; roles: string; age: string; version: string; cpu: string; memory: string; }
interface CronJobInfo { name: string; schedule: string; last_schedule: string; active: number; suspended: boolean; }

const Modal: React.FC<{ isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode; size?: 'md' | 'lg' | 'xl' }> = ({ isOpen, onClose, title, children, size = 'lg' }) => {
  if (!isOpen) return null;
  const sizeClass = size === 'xl' ? 'max-w-7xl' : size === 'lg' ? 'max-w-4xl' : 'max-w-2xl';
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={onClose}>
      <div className={`bg-dark-surface border border-dark-border rounded-lg ${sizeClass} w-full max-h-[90vh] overflow-y-auto m-4`} onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-dark-surface border-b border-dark-border px-6 py-4 flex items-center justify-between z-10">
          <h2 className="text-2xl font-bold text-zombie-green">{title}</h2>
          <button onClick={onClose} className="text-dark-text hover:text-zombie-green text-3xl font-bold">&times;</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
};

const AdminDashboard: React.FC = () => {
  /* ─────────────────────────────────────────────────────────────────────────
   * State
   * ───────────────────────────────────────────────────────────────────────── */
  const [plugins, setPlugins] = useState<PluginEntry[]>([]);
  const [services, setServices] = useState<Record<string, boolean>>({});
  const [serviceDetails, setServiceDetails] = useState<Record<string, ServiceDetail>>({});
  const [systemStatus, setSystemStatus] = useState('unknown');
  const [loading, setLoading] = useState(true);
  const [actionLog, setActionLog] = useState<string[]>([]);

  // Kubernetes data
  const [pods, setPods] = useState<PodInfo[]>([]);
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [cronJobs, setCronJobs] = useState<CronJobInfo[]>([]);

  // Modal visibility
  const [showSystemHealth, setShowSystemHealth] = useState(false);
  const [showDistributedComputing, setShowDistributedComputing] = useState(false);
  const [showServiceTopology, setShowServiceTopology] = useState(false);
  const [showPodManager, setShowPodManager] = useState(false);
  const [showCronJobManager, setShowCronJobManager] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const [showAlertCenter, setShowAlertCenter] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);

  const addLog = useCallback((msg: string) => {
    setActionLog(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev].slice(0, 100));
  }, []);

  /* ─────────────────────────────────────────────────────────────────────────
   * Fetch Data
   * ───────────────────────────────────────────────────────────────────────── */
  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        api.get('/ai_brain/plugins/registry'),
        api.get('/admin/status'),
        api.get('/k8s/pods').then(r => r.data),
        api.get('/k8s/nodes').then(r => r.data),
        api.get('/k8s/cronjobs').then(r => r.data),
      ]);

      if (results[0].status === 'fulfilled') setPlugins(results[0].value.data.plugins || []);
      if (results[1].status === 'fulfilled') {
        const data = results[1].value.data;
        setSystemStatus(data.status || 'unknown');
        const svc: Record<string, boolean> = {};
        for (const [key, val] of Object.entries(data)) {
          if (typeof val === 'boolean') svc[key] = val;
        }
        setServices(svc);
        setServiceDetails(data.details || {});
      }
      if (results[2].status === 'fulfilled') setPods(results[2].value || []);
      if (results[3].status === 'fulfilled') setNodes(results[3].value || []);
      if (results[4].status === 'fulfilled') setCronJobs(results[4].value || []);
    } catch (err) {
      console.error('Admin fetch error:', err);
      addLog(`Error fetching data: ${err}`);
    }
    setLoading(false);
  }, [addLog]);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  /* ─────────────────────────────────────────────────────────────────────────
   * Pod Actions
   * ───────────────────────────────────────────────────────────────────────── */
  const restartPod = async (podName: string) => {
    try {
      await api.post(`/k8s/pods/${podName}/restart`);
      addLog(`Restarted pod: ${podName}`);
      fetchAll();
    } catch (err) {
      addLog(`Failed to restart pod ${podName}: ${err}`);
    }
  };

  const deletePod = async (podName: string) => {
    if (!window.confirm(`Delete pod ${podName}?`)) return;
    try {
      await api.delete(`/k8s/pods/${podName}`);
      addLog(`Deleted pod: ${podName}`);
      fetchAll();
    } catch (err) {
      addLog(`Failed to delete pod ${podName}: ${err}`);
    }
  };

  /* ─────────────────────────────────────────────────────────────────────────
   * Service Stats
   * ───────────────────────────────────────────────────────────────────────── */
  const totalServices = Object.keys(services).length;
  const runningServices = Object.values(services).filter(v => v).length;
  const failedServices = totalServices - runningServices;

  const totalPods = pods.length;
  const runningPods = pods.filter(p => p.status === 'Running').length;
  const crashingPods = pods.filter(p => p.status === 'CrashLoopBackOff' || p.restarts > 10).length;
  const pendingPods = pods.filter(p => p.status === 'Pending').length;

  const readyNodes = nodes.filter(n => n.status === 'Ready').length;
  const notReadyNodes = nodes.filter(n => n.status !== 'Ready').length;

  if (loading) return <div className="flex items-center justify-center h-screen text-zombie-green text-2xl">Loading Admin Panel...</div>;

  /* ═══════════════════════════════════════════════════════════════════════════
   * RENDER
   * ═══════════════════════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen bg-dark-bg p-6">
      <h1 className="text-4xl font-bold mb-6 text-zombie-green">Admin Dashboard</h1>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="bg-gradient-to-br from-blue-900/40 to-blue-800/20 border-blue-500/30 cursor-pointer hover:scale-105 transition" onClick={() => setShowSystemHealth(true)}>
          <h3 className="text-lg font-semibold text-blue-300">System Status</h3>
          <p className={`text-3xl font-bold ${systemStatus === 'ok' ? 'text-green-400' : 'text-red-400'}`}>{systemStatus.toUpperCase()}</p>
          <p className="text-sm text-blue-200 mt-1">{runningServices}/{totalServices} services running</p>
        </Card>

        <Card className="bg-gradient-to-br from-purple-900/40 to-purple-800/20 border-purple-500/30 cursor-pointer hover:scale-105 transition" onClick={() => setShowDistributedComputing(true)}>
          <h3 className="text-lg font-semibold text-purple-300">Cluster Nodes</h3>
          <p className="text-3xl font-bold text-purple-100">{nodes.length}</p>
          <p className="text-sm text-purple-200 mt-1">{readyNodes} ready, {notReadyNodes} down</p>
        </Card>

        <Card className="bg-gradient-to-br from-green-900/40 to-green-800/20 border-green-500/30 cursor-pointer hover:scale-105 transition" onClick={() => setShowPodManager(true)}>
          <h3 className="text-lg font-semibold text-green-300">Pods</h3>
          <p className="text-3xl font-bold text-green-100">{totalPods}</p>
          <p className="text-sm text-green-200 mt-1">{runningPods} running, {crashingPods} crashing</p>
        </Card>

        <Card className="bg-gradient-to-br from-red-900/40 to-red-800/20 border-red-500/30 cursor-pointer hover:scale-105 transition" onClick={() => setShowAlertCenter(true)}>
          <h3 className="text-lg font-semibold text-red-300">Alerts</h3>
          <p className="text-3xl font-bold text-red-100">{failedServices + crashingPods + pendingPods}</p>
          <p className="text-sm text-red-200 mt-1">Issues detected</p>
        </Card>
      </div>

      {/* Feature Buttons */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Button variant="primary" onClick={() => setShowServiceTopology(true)}>Service Topology</Button>
        <Button variant="primary" onClick={() => setShowCronJobManager(true)}>CronJobs</Button>
        <Button variant="primary" onClick={() => setShowMetrics(true)}>Metrics</Button>
        <Button variant="primary" onClick={() => setShowQuickActions(true)}>Quick Actions</Button>
      </div>

      {/* Services Overview */}
      <Card className="mb-6">
        <h2 className="text-2xl font-bold mb-4 text-zombie-green">Services Status</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {Object.entries(services).map(([name, status]) => (
            <div key={name} className={`p-3 rounded border ${status ? 'bg-green-900/20 border-green-500/30' : 'bg-red-900/20 border-red-500/30'}`}>
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${status ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-dark-text font-semibold">{name}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Plugins */}
      <Card className="mb-6">
        <h2 className="text-2xl font-bold mb-4 text-zombie-green">Registered Plugins</h2>
        <div className="space-y-2">
          {plugins.map((plugin, idx) => (
            <div key={idx} className="p-3 bg-dark-bg rounded border border-dark-border hover:border-zombie-green/50 transition">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-semibold text-zombie-green">{plugin.name} <span className="text-dark-text/50 text-sm">v{plugin.version}</span></h4>
                  <p className="text-dark-text text-sm">{plugin.description}</p>
                  <p className="text-dark-text/70 text-xs mt-1">URL: {plugin.url}</p>
                </div>
                <div className={`px-3 py-1 rounded text-xs ${plugin.status === 'active' ? 'bg-green-900/30 text-green-400' : 'bg-gray-900/30 text-gray-400'}`}>
                  {plugin.status}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Action Log */}
      <Card>
        <h2 className="text-2xl font-bold mb-4 text-zombie-green">Action Log</h2>
        <div className="bg-black/40 rounded p-3 max-h-64 overflow-y-auto font-mono text-xs">
          {actionLog.map((log, idx) => (
            <div key={idx} className="text-green-400 mb-1">{log}</div>
          ))}
          {actionLog.length === 0 && <div className="text-dark-text/50">No actions yet</div>}
        </div>
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════════
       * MODALS
       * ═══════════════════════════════════════════════════════════════════════════ */}

      {/* System Health Modal */}
      <Modal isOpen={showSystemHealth} onClose={() => setShowSystemHealth(false)} title="System Health" size="xl">
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card className="bg-blue-900/20 border-blue-500/30">
            <div className="text-blue-300 text-sm">Total Services</div>
            <div className="text-3xl font-bold text-blue-100">{totalServices}</div>
          </Card>
          <Card className="bg-green-900/20 border-green-500/30">
            <div className="text-green-300 text-sm">Running</div>
            <div className="text-3xl font-bold text-green-100">{runningServices}</div>
          </Card>
          <Card className="bg-red-900/20 border-red-500/30">
            <div className="text-red-300 text-sm">Failed</div>
            <div className="text-3xl font-bold text-red-100">{failedServices}</div>
          </Card>
        </div>

        <h3 className="text-xl font-bold text-zombie-green mb-3">Service Details</h3>
        <div className="space-y-2">
          {Object.entries(services).map(([name, status]) => (
            <div key={name} className={`p-3 rounded border ${status ? 'bg-green-900/10 border-green-500/20' : 'bg-red-900/10 border-red-500/20'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-4 h-4 rounded-full ${status ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="font-semibold text-dark-text">{name}</span>
                </div>
                {serviceDetails[name] && (
                  <div className="text-xs text-dark-text/70">
                    Checked: {new Date(serviceDetails[name].checked_at).toLocaleTimeString()}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </Modal>

      {/* Distributed Computing Modal */}
      <Modal isOpen={showDistributedComputing} onClose={() => setShowDistributedComputing(false)} title="Distributed Computing" size="xl">
        <h3 className="text-xl font-bold text-zombie-green mb-3">Cluster Nodes</h3>
        <div className="space-y-3">
          {nodes.map((node, idx) => (
            <div key={idx} className={`p-4 rounded border ${node.status === 'Ready' ? 'bg-green-900/10 border-green-500/30' : 'bg-red-900/10 border-red-500/30'}`}>
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-lg font-semibold text-zombie-green">{node.name}</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm text-dark-text mt-2">
                    <div>Status: <span className={node.status === 'Ready' ? 'text-green-400' : 'text-red-400'}>{node.status}</span></div>
                    <div>Roles: {node.roles}</div>
                    <div>Age: {node.age}</div>
                    <div>Version: {node.version}</div>
                    <div>CPU: {node.cpu}</div>
                    <div>Memory: {node.memory}</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <h3 className="text-xl font-bold text-zombie-green mb-3 mt-6">Pod Distribution</h3>
        <div className="space-y-2">
          {nodes.map(node => {
            const nodePods = pods.filter(p => p.node === node.name);
            return (
              <div key={node.name} className="p-3 bg-dark-bg rounded border border-dark-border">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-dark-text">{node.name}</span>
                  <span className="text-zombie-green">{nodePods.length} pods</span>
                </div>
              </div>
            );
          })}
        </div>
      </Modal>

      {/* Service Topology Modal */}
      <Modal isOpen={showServiceTopology} onClose={() => setShowServiceTopology(false)} title="Service Topology" size="xl">
        <div className="mb-4 p-4 bg-blue-900/20 border border-blue-500/30 rounded">
          <h4 className="font-semibold text-blue-300 mb-2">Service Architecture</h4>
          <p className="text-dark-text text-sm">Gateway (8000) → AI Brain (9004) → LLM (11434)</p>
          <p className="text-dark-text text-sm">Gateway (8000) → Microservices (meds:9000, habits:9000, reminder:9002, financial:9005)</p>
          <p className="text-dark-text text-sm">Gateway (8000) → Plugins (security:8001, drone:8002, briefing:8003)</p>
        </div>

        <h3 className="text-xl font-bold text-zombie-green mb-3">Service Dependencies</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {['gateway', 'ai_brain', 'meds', 'reminder', 'habits', 'financial', 'library_of_truth', 'cam', 'ml', 'voice'].map(svc => (
            <div key={svc} className={`p-3 rounded border ${services[svc] ? 'bg-green-900/10 border-green-500/20' : 'bg-red-900/10 border-red-500/20'}`}>
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${services[svc] ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="font-semibold text-dark-text">{svc}</span>
              </div>
            </div>
          ))}
        </div>
      </Modal>

      {/* Pod Manager Modal */}
      <Modal isOpen={showPodManager} onClose={() => setShowPodManager(false)} title="Pod Manager" size="xl">
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Card className="bg-blue-900/20"><div className="text-blue-300 text-sm">Total</div><div className="text-2xl font-bold">{totalPods}</div></Card>
          <Card className="bg-green-900/20"><div className="text-green-300 text-sm">Running</div><div className="text-2xl font-bold">{runningPods}</div></Card>
          <Card className="bg-red-900/20"><div className="text-red-300 text-sm">Crashing</div><div className="text-2xl font-bold">{crashingPods}</div></Card>
          <Card className="bg-yellow-900/20"><div className="text-yellow-300 text-sm">Pending</div><div className="text-2xl font-bold">{pendingPods}</div></Card>
        </div>

        <div className="space-y-2 max-h-96 overflow-y-auto">
          {pods.map((pod, idx) => (
            <div key={idx} className={`p-3 rounded border ${
              pod.status === 'Running' ? 'bg-green-900/10 border-green-500/20' :
              pod.status === 'CrashLoopBackOff' ? 'bg-red-900/10 border-red-500/20' :
              pod.status === 'Pending' ? 'bg-yellow-900/10 border-yellow-500/20' :
              'bg-gray-900/10 border-gray-500/20'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold text-dark-text">{pod.name}</h4>
                  <div className="grid grid-cols-4 gap-2 text-xs text-dark-text/70 mt-1">
                    <div>Status: <span className={pod.status === 'Running' ? 'text-green-400' : 'text-red-400'}>{pod.status}</span></div>
                    <div>Ready: {pod.ready}</div>
                    <div>Restarts: {pod.restarts}</div>
                    <div>Node: {pod.node}</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  {pod.status === 'CrashLoopBackOff' && <Button variant="primary" size="sm" onClick={() => restartPod(pod.name)}>Restart</Button>}
                  <Button variant="danger" size="sm" onClick={() => deletePod(pod.name)}>Delete</Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Modal>

      {/* CronJob Manager Modal */}
      <Modal isOpen={showCronJobManager} onClose={() => setShowCronJobManager(false)} title="CronJob Manager" size="xl">
        <div className="space-y-3">
          {cronJobs.map((job, idx) => (
            <div key={idx} className="p-4 bg-dark-bg rounded border border-dark-border">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-lg font-semibold text-zombie-green">{job.name}</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm text-dark-text mt-2">
                    <div>Schedule: {job.schedule}</div>
                    <div>Last Run: {job.last_schedule || 'Never'}</div>
                    <div>Active Jobs: {job.active}</div>
                    <div>Suspended: {job.suspended ? 'Yes' : 'No'}</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {cronJobs.length === 0 && <p className="text-dark-text/50">No CronJobs found</p>}
        </div>
      </Modal>

      {/* Metrics Modal */}
      <Modal isOpen={showMetrics} onClose={() => setShowMetrics(false)} title="Real-time Metrics" size="xl">
        <h3 className="text-xl font-bold text-zombie-green mb-3">Resource Usage</h3>
        <div className="grid grid-cols-2 gap-4">
          {nodes.map(node => (
            <Card key={node.name} className="bg-dark-bg">
              <h4 className="font-semibold text-zombie-green mb-2">{node.name}</h4>
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-sm text-dark-text mb-1">
                    <span>CPU</span>
                    <span>{node.cpu}</span>
                  </div>
                  <div className="w-full bg-dark-surface rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: node.cpu }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm text-dark-text mb-1">
                    <span>Memory</span>
                    <span>{node.memory}</span>
                  </div>
                  <div className="w-full bg-dark-surface rounded-full h-2">
                    <div className="bg-purple-500 h-2 rounded-full" style={{ width: node.memory }} />
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Modal>

      {/* Alert Center Modal */}
      <Modal isOpen={showAlertCenter} onClose={() => setShowAlertCenter(false)} title="Alert Center" size="xl">
        <div className="space-y-3">
          {failedServices > 0 && (
            <div className="p-4 bg-red-900/20 border border-red-500/30 rounded">
              <h4 className="font-semibold text-red-400 mb-2">Failed Services ({failedServices})</h4>
              <ul className="list-disc list-inside text-dark-text text-sm">
                {Object.entries(services).filter(([_, status]) => !status).map(([name]) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </div>
          )}

          {crashingPods > 0 && (
            <div className="p-4 bg-red-900/20 border border-red-500/30 rounded">
              <h4 className="font-semibold text-red-400 mb-2">Crashing Pods ({crashingPods})</h4>
              <ul className="list-disc list-inside text-dark-text text-sm">
                {pods.filter(p => p.status === 'CrashLoopBackOff' || p.restarts > 10).map(p => (
                  <li key={p.name}>{p.name} - {p.restarts} restarts</li>
                ))}
              </ul>
            </div>
          )}

          {pendingPods > 0 && (
            <div className="p-4 bg-yellow-900/20 border border-yellow-500/30 rounded">
              <h4 className="font-semibold text-yellow-400 mb-2">Pending Pods ({pendingPods})</h4>
              <ul className="list-disc list-inside text-dark-text text-sm">
                {pods.filter(p => p.status === 'Pending').map(p => (
                  <li key={p.name}>{p.name}</li>
                ))}
              </ul>
            </div>
          )}

          {notReadyNodes > 0 && (
            <div className="p-4 bg-orange-900/20 border border-orange-500/30 rounded">
              <h4 className="font-semibold text-orange-400 mb-2">Nodes Down ({notReadyNodes})</h4>
              <ul className="list-disc list-inside text-dark-text text-sm">
                {nodes.filter(n => n.status !== 'Ready').map(n => (
                  <li key={n.name}>{n.name} - {n.status}</li>
                ))}
              </ul>
            </div>
          )}

          {failedServices === 0 && crashingPods === 0 && pendingPods === 0 && notReadyNodes === 0 && (
            <div className="p-4 bg-green-900/20 border border-green-500/30 rounded">
              <h4 className="font-semibold text-green-400">All systems operational</h4>
              <p className="text-dark-text text-sm mt-1">No alerts at this time</p>
            </div>
          )}
        </div>
      </Modal>

      {/* Quick Actions Modal */}
      <Modal isOpen={showQuickActions} onClose={() => setShowQuickActions(false)} title="Quick Actions" size="md">
        <div className="grid grid-cols-2 gap-3">
          <Button variant="primary" onClick={() => { fetchAll(); addLog('Refreshed all data'); }}>Refresh Data</Button>
          <Button variant="primary" onClick={() => { window.open('http://192.168.68.57:30002/guardian/dashboard', '_blank'); }}>Open Chat</Button>
          <Button variant="primary" onClick={async () => { try { await api.post('/briefing/generate'); addLog('Generated briefing'); fetchAll(); } catch (e) { addLog('Failed to generate briefing'); } }}>Generate Briefing</Button>
          <Button variant="danger" onClick={() => { if (window.confirm('Restart all crashing pods?')) { pods.filter(p => p.status === 'CrashLoopBackOff').forEach(p => restartPod(p.name)); } }}>Restart Crashing Pods</Button>
          <Button variant="danger" onClick={() => { if (window.confirm('Delete all pending pods?')) { pods.filter(p => p.status === 'Pending').forEach(p => deletePod(p.name)); } }}>Clear Pending Pods</Button>
          <Button variant="secondary" onClick={() => { actionLog.length = 0; setActionLog([]); }}>Clear Logs</Button>
        </div>
      </Modal>
    </div>
  );
};

export default AdminDashboard;
