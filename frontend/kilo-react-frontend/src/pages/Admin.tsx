import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { WebcamMonitor } from '../components/shared/WebcamMonitor';
import { Modal } from '../components/shared/Modal';
import { SystemStatus } from '../types';
import api from '../services/api';
import { useDeviceDetection } from '../utils/deviceDetection';

const Admin: React.FC = () => {
  const navigate = useNavigate();
  const { deviceInfo, features } = useDeviceDetection();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [memoryStats, setMemoryStats] = useState({ total: 0, public: 0, private: 0, confidential: 0 });
  const [loading, setLoading] = useState(true);
  const [mlTestResult, setMlTestResult] = useState<any>(null);
  const [mlTestHabitName, setMlTestHabitName] = useState('Exercise');
  const [mlTesting, setMlTesting] = useState(false);
  // Camera modal state
  const [cameraModalOpen, setCameraModalOpen] = useState(false);
  const openCameraModal = () => setCameraModalOpen(true);
  const closeCameraModal = () => setCameraModalOpen(false);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const statusRes = await api.get('/admin/status');
      setSystemStatus(statusRes.data);

      // Mock memory stats - replace with actual API call
      setMemoryStats({
        total: 1234,
        public: 800,
        private: 300,
        confidential: 134,
      });
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const createBackup = async () => {
    try {
      await api.post('/admin/backup');
      alert('Backup created successfully!');
    } catch (error) {
      console.error('Failed to create backup:', error);
      alert('Failed to create backup');
    }
  };

  const testMLPrediction = async () => {
    setMlTesting(true);
    setMlTestResult(null);

    try {
      // Test habit completion prediction
      const response = await api.post('/ml/predict/habit_completion', {
        habit_id: 999,
        habit_name: mlTestHabitName,
        current_streak: 5,
        completions_this_week: 4,
        target_count: 1,
        frequency: 'daily'
      });

      setMlTestResult(response.data);
    } catch (error) {
      console.error('ML prediction test failed:', error);
      setMlTestResult({ error: 'Test failed' });
    } finally {
      setMlTesting(false);
    }
  };

  const StatusIndicator: React.FC<{ status: boolean; label: string }> = ({ status, label }) => (
    <div className="flex items-center justify-between p-4 bg-dark-bg border border-dark-border rounded-lg">
      <span className="text-lg font-semibold text-zombie-green">{label}</span>
      <div className={`w-6 h-6 rounded-full ${status ? 'bg-green-500 shadow-lg shadow-green-500/50' : 'bg-red-500 shadow-lg shadow-red-500/50'}`}></div>
    </div>
  );

  return (
    <div className="min-h-screen zombie-gradient p-6">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-zombie-green terminal-glow">⚙️ ADMIN PANEL</h1>
          <span className="text-xs px-2 py-1 rounded-full bg-dark-border text-zombie-green border border-zombie-green">
            {deviceInfo.type === 'tablet' ? '📱 Tablet Mode' : '💻 Full Access'}
          </span>
        </div>
        <Button onClick={() => navigate('/')} variant="secondary" size="sm">
          ← BACK
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-zombie-green">Loading admin data...</div>
      ) : (
        <>
          {/* System Status */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">SYSTEM STATUS:</h2>
            <Card className="space-y-3">
              {systemStatus && (
                <>
                  <StatusIndicator status={systemStatus.gateway} label="Gateway" />
                  <StatusIndicator status={systemStatus.ai_brain} label="AI Brain" />
                  <StatusIndicator status={systemStatus.meds} label="Medications" />
                  <StatusIndicator status={systemStatus.reminders} label="Reminders" />
                  <StatusIndicator status={systemStatus.finance} label="Finance" />
                  <StatusIndicator status={systemStatus.habits} label="Habits" />
                </>
              )}
            </Card>
          </div>

          {/* Memory Statistics */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">MEMORY STATISTICS:</h2>
            <Card>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-dark-bg border border-blue-600 rounded-lg">
                  <p className="text-sm text-zombie-green">TOTAL MEMORIES</p>
                  <p className="text-4xl font-bold text-blue-600">{memoryStats.total}</p>
                </div>
                <div className="text-center p-4 bg-dark-bg border border-green-600 rounded-lg">
                  <p className="text-sm text-zombie-green">PUBLIC</p>
                  <p className="text-4xl font-bold text-green-600">{memoryStats.public}</p>
                </div>
                <div className="text-center p-4 bg-dark-bg border border-yellow-600 rounded-lg">
                  <p className="text-sm text-zombie-green">PRIVATE</p>
                  <p className="text-4xl font-bold text-yellow-600">{memoryStats.private}</p>
                </div>
                <div className="text-center p-4 bg-dark-bg border border-red-600 rounded-lg">
                  <p className="text-sm text-zombie-green">CONFIDENTIAL</p>
                  <p className="text-4xl font-bold text-red-600">{memoryStats.confidential}</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Admin Actions */}
          {features.showAdvancedFeatures && (
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">ADMIN ACTIONS:</h2>
              <div className="grid grid-cols-3 gap-4">
                <Button onClick={createBackup} variant="primary" size="lg" className="h-24">
                  💾 CREATE BACKUP
                </Button>
                <Button onClick={() => {}} variant="secondary" size="lg" className="h-24">
                  🔄 RESTORE BACKUP
                </Button>

                {/* Camera Card embedded in Admin Actions (inline feed) - Server only */}
                {features.showServerCamera && (
                  <Card className="h-24 p-2 overflow-hidden">
                    <div className="w-full h-full flex items-center">
                      <div className="w-full">
                        <h3 className="text-sm text-zombie-green font-semibold mb-1">📷 Server Camera</h3>
                        <div className="text-xs text-gray-400 mb-2">Live feed</div>
                        <div className="w-full h-12 overflow-hidden rounded-md border border-dark-border relative cursor-pointer" onClick={openCameraModal}>
                          <WebcamMonitor compact floating={false} widthClass={'w-full'} heightClass={'h-12'} className={'w-full h-12'} onClick={openCameraModal} />
                          <div className="absolute top-1 right-1 z-50">
                            <button onClick={(e) => { e.stopPropagation(); openCameraModal(); }} className="px-2 py-1 bg-dark-border text-zombie-green text-xs rounded hover:bg-zombie-green/10">Open</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                )}

                <Button onClick={() => {}} variant="danger" size="lg" className="h-24">
                  🗑️ CLEAR CACHE
                </Button>
                <Button onClick={() => {}} variant="secondary" size="lg" className="h-24">
                  📊 VIEW LOGS
                </Button>
              </div>
            </div>
          )}

          {/* Camera Modal (expanded preview) - Server only */}
          {features.showServerCamera && (
            <Modal open={cameraModalOpen} onClose={closeCameraModal} title="Server Camera Preview">
              <div className="w-full">
                <WebcamMonitor floating={false} widthClass={'w-full'} heightClass={'h-96'} className={'w-full h-96'} />
              </div>
            </Modal>
          )}

          {/* ML Prediction Testing - Advanced feature only */}
          {features.showAdvancedFeatures && (
            <div className="mb-6">
            <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">🤖 ML PREDICTION TESTING:</h2>
            <Card>
              <div className="space-y-4">
                <div>
                  <label className="block text-zombie-green font-semibold mb-2">Test Habit Name:</label>
                  <input
                    type="text"
                    value={mlTestHabitName}
                    onChange={(e) => setMlTestHabitName(e.target.value)}
                    className="w-full px-4 py-3 text-lg rounded-lg border-2 border-dark-border bg-dark-bg text-zombie-green placeholder-zombie-green placeholder-opacity-50 focus:border-zombie-green focus:outline-none"
                    placeholder="e.g., Exercise, Meditation"
                  />
                </div>

                <Button
                  onClick={testMLPrediction}
                  variant="primary"
                  size="lg"
                  className="w-full"
                  disabled={mlTesting}
                >
                  {mlTesting ? '⏳ TESTING...' : '🧪 TEST ML PREDICTION'}
                </Button>

                {mlTestResult && (
                  <div className="mt-4 p-4 bg-dark-bg border-2 border-blue-500 rounded-lg">
                    {mlTestResult.error ? (
                      <p className="text-red-500 font-bold">❌ {mlTestResult.error}</p>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-zombie-green font-semibold">Habit:</span>
                          <span className="text-white">{mlTestHabitName}</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-zombie-green font-semibold">Completion Probability:</span>
                          <span className="text-white text-2xl font-bold">
                            {Math.round(mlTestResult.completion_probability * 100)}%
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-zombie-green font-semibold">Confidence:</span>
                          <span className={`font-bold ${mlTestResult.confidence === 'high' ? 'text-green-500' : mlTestResult.confidence === 'medium' ? 'text-yellow-500' : 'text-orange-500'}`}>
                            {mlTestResult.confidence.toUpperCase()}
                          </span>
                        </div>
                        <div className="mt-3 p-3 bg-blue-900 bg-opacity-50 rounded">
                          <p className="text-blue-200 text-sm">
                            💡 {mlTestResult.recommendation}
                          </p>
                        </div>
                        {mlTestResult.should_send_reminder && (
                          <div className="flex items-center gap-2 text-yellow-400">
                            <span>🔔</span>
                            <span className="text-sm">Reminder recommended</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Card>
          </div>
          )}

          {/* USB Data Transfer */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-zombie-green terminal-glow mb-4">💾 USB DATA TRANSFER:</h2>
            <Card>
              <div className="space-y-4">
                <div className="text-center p-4 bg-yellow-900 bg-opacity-50 border border-yellow-600 rounded-lg">
                  <p className="text-yellow-200 font-semibold">
                    🔒 SECURE AIR-GAPPED DATA EXPORT
                  </p>
                  <p className="text-yellow-300 text-sm mt-2">
                    Export therapy progress data to USB drives for sharing with healthcare providers.
                    All data is encrypted and password-protected.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Button
                    onClick={() => navigate('/usb-export')}
                    variant="primary"
                    size="lg"
                    className="h-20 flex flex-col items-center justify-center"
                  >
                    <span className="text-2xl mb-1">📤</span>
                    <span className="text-sm font-bold">EXPORT DATA</span>
                    <span className="text-xs">To USB Drive</span>
                  </Button>

                  <Button
                    onClick={() => navigate('/usb-import')}
                    variant="secondary"
                    size="lg"
                    className="h-20 flex flex-col items-center justify-center"
                  >
                    <span className="text-2xl mb-1">📥</span>
                    <span className="text-sm font-bold">IMPORT DATA</span>
                    <span className="text-xs">From USB Drive</span>
                  </Button>

                  <Button
                    onClick={() => navigate('/usb-settings')}
                    variant="secondary"
                    size="lg"
                    className="h-20 flex flex-col items-center justify-center"
                  >
                    <span className="text-2xl mb-1">⚙️</span>
                    <span className="text-sm font-bold">USB SETTINGS</span>
                    <span className="text-xs">Password & Security</span>
                  </Button>
                </div>

                <div className="text-center text-sm text-gray-400">
                  <p>💡 Default password is generated on first use and logged to console.</p>
                  <p>🔐 Change password immediately for security.</p>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}


    </div>
  );
};

export default Admin;
