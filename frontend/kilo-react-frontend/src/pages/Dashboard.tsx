import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatService } from '../services/chatService';
import { Message } from '../types';
import { Button } from '../components/shared/Button';
import api from '../services/api';
import { io } from 'socket.io-client';
import { CoachingInsight } from '../types';
import { useDeviceDetection } from '../utils/deviceDetection';

const STICKY_COLORS = [
  'bg-yellow-200 border-yellow-400 text-yellow-900',
  'bg-green-200 border-green-400 text-green-900',
  'bg-blue-200 border-blue-400 text-blue-900',
  'bg-pink-200 border-pink-400 text-pink-900',
  'bg-purple-200 border-purple-400 text-purple-900',
];

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem('dashboard-chat-messages');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) }));
      } catch {
        return [{ id: '1', role: 'ai', content: "Hey Kyle! I'm Kilo, your AI assistant. How can I help you today?", timestamp: new Date() }];
      }
    }
    return [{ id: '1', role: 'ai', content: "Hey Kyle! I'm Kilo, your AI assistant. How can I help you today?", timestamp: new Date() }];
  });

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<CoachingInsight[]>([]);
  const [reminders, setReminders] = useState<any[]>([]);
  const [showReminders, setShowReminders] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const { features } = useDeviceDetection();

  useEffect(() => {
    const socket = io(process.env.REACT_APP_API_URL || window.location.origin, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
    });
    socket.on('insight_generated', (insight: CoachingInsight) => {
      setInsights(prev => [insight, ...prev].slice(0, 10));
    });
    return () => { socket.close(); };
  }, []);

  const fetchReminders = useCallback(async () => {
    try {
      const res = await api.get('/reminder/notifications/pending');
      const raw: any[] = Array.isArray(res.data) ? res.data : (res.data?.notifications || []);
      setReminders(raw);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchReminders();
    const t = setInterval(fetchReminders, 30000);
    return () => clearInterval(t);
  }, [fetchReminders]);

  useEffect(() => {
    const c = messagesContainerRef.current;
    if (c) c.scrollTo({ top: c.scrollHeight, behavior: 'smooth' });
    localStorage.setItem('dashboard-chat-messages', JSON.stringify(messages));
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    try {
      const response = await chatService.sendMessage(input);
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'ai', content: response, timestamp: new Date() }]);
    } catch {
      setMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'ai', content: 'Sorry, hit an error. Try again.', timestamp: new Date() }]);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: string) => {
    if (!ts) return '';
    try {
      return new Date(ts.replace(' ', 'T')).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    } catch { return ts.slice(11, 16); }
  };

  return (
    <div className="h-screen zombie-gradient flex flex-col p-3 gap-3 overflow-hidden">

      {/* Header */}
      <div className="flex justify-between items-center flex-shrink-0">
        <h1 className="text-2xl font-bold text-zombie-green terminal-glow">🧠 KILO</h1>
        {features.showFullAdminPanel && (
          <Button onClick={() => navigate('/admin')} variant="secondary" size="sm">⚙️ ADMIN</Button>
        )}
      </div>

      {/* Kilo's Thoughts bar */}
      <div className="flex-shrink-0">
        <div className="text-xs font-bold text-zombie-green uppercase tracking-widest mb-1 px-1">
          🧠 Kilo's Thoughts
        </div>
        <div className="border border-zombie-green border-opacity-30 rounded-xl bg-dark-border bg-opacity-40 h-24 overflow-y-auto px-3 py-2">
          {insights.length === 0 ? (
            <p className="text-xs text-gray-600 italic mt-2">Watching for activity...</p>
          ) : (
            <div className="space-y-2">
              {insights.map((ins, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs text-gray-300 border-b border-dark-border pb-1 last:border-0">
                  <span className="flex-shrink-0">
                    {(ins as any).observation_type === 'medication_reminder' ? '💊' : '💡'}
                  </span>
                  <span className="leading-relaxed">{(ins as any).content || ins.message}</span>
                  <button
                    onClick={() => setInsights(prev => prev.filter((_, i) => i !== idx))}
                    className="ml-auto flex-shrink-0 text-gray-600 hover:text-gray-400"
                  >✕</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat panel — full width, no sidebar eating space */}
      <div className="flex-1 flex flex-col overflow-hidden border border-dark-border rounded-xl bg-dark-border bg-opacity-30 min-h-0">
        <div className="px-4 py-2 border-b border-dark-border flex-shrink-0">
          <h2 className="text-sm font-semibold text-zombie-green terminal-glow">💬 Chat with Kilo</h2>
        </div>

        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[75%] px-4 py-3 rounded-2xl border-2 text-base leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-zombie-green text-dark-bg border-zombie-green rounded-br-none'
                  : 'bg-dark-border text-zombie-green border-dark-border rounded-bl-none'
              }`}>
                <span className="mr-2">{msg.role === 'user' ? '👤' : '🤖'}</span>
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-dark-border border-2 border-dark-border px-4 py-3 rounded-2xl rounded-bl-none flex items-center gap-2">
                <span>🤖</span>
                <div className="flex gap-1">
                  {[0, 150, 300].map(d => (
                    <div key={d} className="w-2 h-2 bg-zombie-green rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-3 border-t border-dark-border flex gap-2 flex-shrink-0">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Message Kilo..."
            className="flex-1 px-4 py-3 rounded-xl border-2 border-dark-border bg-dark-bg text-zombie-green placeholder-zombie-green placeholder-opacity-40 focus:border-zombie-green focus:outline-none text-base"
            disabled={loading}
          />
          <Button onClick={sendMessage} disabled={loading || !input.trim()} size="lg" variant="primary">
            ➤
          </Button>
        </div>
      </div>

      {/* ── Reminders overlay drawer ── fixed to right edge, floats over everything */}
      <div className="fixed top-0 right-0 h-full flex z-50 pointer-events-none">

        {/* Sliding panel — slides in from the right */}
        <div
          className="pointer-events-auto h-full bg-gray-900 border-l border-zombie-green border-opacity-40 shadow-2xl overflow-y-auto transition-all duration-300 ease-in-out flex flex-col gap-3 py-4 px-3"
          style={{ width: showReminders ? '220px' : '0px', opacity: showReminders ? 1 : 0, overflow: showReminders ? 'auto' : 'hidden' }}
        >
          <div className="text-xs font-bold text-zombie-green uppercase tracking-widest whitespace-nowrap">
            📌 Today's Reminders
          </div>
          {reminders.length === 0 ? (
            <div className="text-xs text-gray-500 italic whitespace-nowrap">Nothing due today</div>
          ) : (
            reminders.map((r, idx) => (
              <div
                key={r.id || idx}
                className={`rounded-lg border-2 p-3 shadow-md flex-shrink-0 transform ${
                  idx % 2 === 0 ? 'rotate-1' : '-rotate-1'
                } ${STICKY_COLORS[idx % STICKY_COLORS.length]}`}
                style={{ minWidth: '180px' }}
              >
                <div className="text-xs font-bold mb-1 opacity-60">{formatTime(r.timestamp)}</div>
                <p className="text-xs font-medium leading-snug">{r.message}</p>
              </div>
            ))
          )}
        </div>

        {/* Pull tab — always visible */}
        <button
          onClick={() => setShowReminders(prev => !prev)}
          className="pointer-events-auto self-center flex-shrink-0 flex flex-col items-center justify-center gap-2 bg-gray-900 border border-zombie-green border-opacity-50 border-r-0 rounded-l-xl w-7 py-5 text-zombie-green hover:bg-zombie-green hover:text-dark-bg transition-colors shadow-lg"
          title={showReminders ? 'Hide reminders' : 'Show reminders'}
        >
          {reminders.length > 0 && (
            <span className="bg-zombie-green text-dark-bg rounded-full w-4 h-4 flex items-center justify-center text-xs font-bold leading-none">
              {reminders.length}
            </span>
          )}
          <span className="text-xs" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
            Reminders
          </span>
          <span className="text-sm font-bold">{showReminders ? '›' : '‹'}</span>
        </button>

      </div>

    </div>
  );
};

export default Dashboard;
