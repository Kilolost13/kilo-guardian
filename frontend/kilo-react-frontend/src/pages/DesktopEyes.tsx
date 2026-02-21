import React, { useState, useEffect } from 'react';
import { Card } from '../components/shared/Card';
import { Button } from '../components/shared/Button';
import api from '../services/api';

interface Observation {
  type: string;
  content: string;
  priority: string;
  metadata: Record<string, any>;
  timestamp: string;
}

const DesktopEyes: React.FC = () => {
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchObservations = async () => {
    try {
      const response = await api.get('/ai_brain/observations?limit=50');
      setObservations(response.data.observations.reverse()); // Most recent first
      setLoading(false);
    } catch (error) {
      console.error('Error fetching observations:', error);
      setLoading(false);
    }
  };

  const clearObservations = async () => {
    try {
      await api.delete('/ai_brain/observations');
      setObservations([]);
    } catch (error) {
      console.error('Error clearing observations:', error);
    }
  };

  useEffect(() => {
    fetchObservations();
    const interval = autoRefresh ? setInterval(fetchObservations, 5000) : null;
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-400';
      case 'normal': return 'text-zombie-green';
      case 'low': return 'text-gray-400';
      default: return 'text-white';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'window_observation': return '🪟';
      case 'file_observation': return '📁';
      case 'test': return '🧪';
      default: return '👁️';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-header text-zombie-green mb-6">KILO DESKTOP EYES 👁️</h1>
        <p className="text-dark-text">Loading observations...</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-header text-zombie-green mb-2">KILO DESKTOP EYES 👁️😈</h1>
          <p className="text-dark-text text-sm">Kilo is watching your desktop activity...</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            variant={autoRefresh ? 'primary' : 'secondary'}
            size="sm"
          >
            {autoRefresh ? '🔄 Auto-refresh ON' : '⏸️ Auto-refresh OFF'}
          </Button>
          <Button onClick={fetchObservations} variant="secondary" size="sm">
            🔃 Refresh
          </Button>
          <Button onClick={clearObservations} variant="danger" size="sm">
            🗑️ Clear All
          </Button>
        </div>
      </div>

      {observations.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-dark-text text-lg mb-2">No observations yet</p>
          <p className="text-dark-text-secondary text-sm">
            Start kilo_desktop_eyes.py on your machine to begin monitoring
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {observations.map((obs, idx) => (
            <Card 
              key={idx} 
              className={`p-4 border-l-4 ${
                obs.priority === 'high' ? 'border-red-500' : 
                obs.priority === 'low' ? 'border-gray-500' : 
                'border-zombie-green'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className="text-3xl">{getTypeIcon(obs.type)}</div>
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <span className={`font-mono text-sm ${getPriorityColor(obs.priority)}`}>
                        [{obs.priority.toUpperCase()}]
                      </span>
                      <span className="ml-2 text-dark-text-secondary text-xs">
                        {obs.type.replace('_', ' ')}
                      </span>
                    </div>
                    <span className="text-dark-text-secondary text-xs">
                      {formatTimestamp(obs.timestamp)}
                    </span>
                  </div>
                  <p className="text-white text-base mb-2">{obs.content}</p>
                  {Object.keys(obs.metadata).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-zombie-green text-sm cursor-pointer hover:underline">
                        View metadata
                      </summary>
                      <pre className="mt-2 p-2 bg-dark-bg rounded text-xs text-dark-text-secondary overflow-x-auto">
                        {JSON.stringify(obs.metadata, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default DesktopEyes;
