import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { chatService } from '../services/chatService';
import { Message } from '../types';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { CameraCapture } from '../components/shared/CameraCapture';
import api from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { io } from 'socket.io-client';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { RealTimeUpdate, CoachingInsight } from '../types';
import { useDeviceDetection } from '../utils/deviceDetection';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  
  // Load chat messages from localStorage on mount
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem('dashboard-chat-messages');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        }));
      } catch {
        return [{ id: '1', role: 'ai', content: "Hey Kyle! I'm Kilo, your AI assistant. How can I help you today?", timestamp: new Date() }];
      }
    }
    return [{ id: '1', role: 'ai', content: "Hey Kyle! I'm Kilo, your AI assistant. How can I help you today?", timestamp: new Date() }];
  });
  
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [insights, setInsights] = useState<CoachingInsight[]>([]);
  const [stats, setStats] = useState<{
    totalMemories: number;
    activeHabits: number;
    upcomingReminders: number;
    monthlySpending: number;
    insightsGenerated: number;
  }>({ totalMemories: 0, activeHabits: 0, upcomingReminders: 0, monthlySpending: 0, insightsGenerated: 0 });

  // Weekly schedule data
  const [weeklySchedule, setWeeklySchedule] = useState<any[]>([]);
  const [selectedDay, setSelectedDay] = useState<any>(null);
  const [showDayModal, setShowDayModal] = useState(false);

  // Real-time socket and updates
  const [realTimeUpdates, setRealTimeUpdates] = useState<{ type: string; message?: string }[]>([]);

  // Voice input (speech recognition)
  const [showVoiceInput, setShowVoiceInput] = useState(false);
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  // Device detection
  const { deviceInfo, features } = useDeviceDetection();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const handleVoiceSubmit = useCallback(async (voiceText: string) => {
    if (!voiceText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: `🎤 ${voiceText}`,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await chatService.sendMessage(voiceText);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to process voice input:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: "Sorry, I couldn't process your voice input.",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
      resetTranscript();
      setShowVoiceInput(false);
    }
  }, [resetTranscript]);

  useEffect(() => {
    if (transcript && !listening) {
      handleVoiceSubmit(transcript);
    }
  }, [transcript, listening, handleVoiceSubmit]);

  const toggleVoiceInput = () => {
    if (!browserSupportsSpeechRecognition) {
      alert('Voice input is not supported in this browser.');
      return;
    }

    if (listening) {
      SpeechRecognition.stopListening();
      setShowVoiceInput(false);
    } else {
      resetTranscript();
      SpeechRecognition.startListening({ continuous: false });
      setShowVoiceInput(true);
    }
  }; 

  const scrollToBottom = () => {
    // Scroll only the chat container, not the entire window
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
      return;
    }
    // Fallback: still try to scroll the marker into view
    const el = messagesEndRef.current;
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
    // Save messages to localStorage whenever they change
    localStorage.setItem('dashboard-chat-messages', JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    fetchStats();
    fetchWeeklySchedule();
  }, []);

  useEffect(() => {
    const newSocket = io(process.env.REACT_APP_API_URL || window.location.origin, {
      path: '/socket.io',
      transports: ['websocket', 'polling']
    });

    newSocket.on('connect', () => {
      console.log('Connected to real-time updates');
    });

    newSocket.on('memory_update', (update: RealTimeUpdate) => {
      setRealTimeUpdates(prev => [update, ...prev].slice(0, 10));
      fetchStats();
    });

    newSocket.on('insight_generated', (insight: CoachingInsight) => {
      setInsights(prev => [insight, ...prev].slice(0, 5));
    });


    return () => {
      newSocket.close();
    };
  }, []);

  const fetchStats = async () => {
    try {
      const response = await api.get('/ai_brain/stats/dashboard');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchWeeklySchedule = async () => {
    try {
      // Calculate start date (Monday of this week)
      const today = new Date();
      const currentDayOfWeek = today.getDay();
      const startDate = new Date(today);
      if (currentDayOfWeek !== 1) {
        startDate.setDate(today.getDate() - currentDayOfWeek + (currentDayOfWeek === 0 ? -6 : 1));
      }
      const startDateStr = startDate.toISOString().split('T')[0];
      
      // Fetch reminders, habits, and bills for the next 7 days
      const [remindersRes, habitsRes, financialRes] = await Promise.all([
        api.get(`/reminder/reminders/week?start_date=${startDateStr}`).catch(() => ({ data: [] })),
        api.get('/habits').catch(() => ({ data: [] })),
        api.get('/financial/transactions').catch(() => ({ data: [] }))
      ]);

      // Build 7-day schedule starting from Monday
      const schedule = [];
      
      for (let i = 0; i < 7; i++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + i);
        const dateStr = date.toISOString().split('T')[0];
        const todayStr = today.toISOString().split('T')[0];
        const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
        const isToday = dateStr === todayStr;

        // Categorize events by time of day
        const morning: any[] = [];   // 5am-12pm
        const afternoon: any[] = [];  // 12pm-5pm
        const evening: any[] = [];    // 5pm-11pm

        // Process reminders (already expanded by backend)
        const reminders = Array.isArray(remindersRes.data) ? remindersRes.data : [];
        reminders.forEach((r: any) => {
          if (r.when && r.when.startsWith(dateStr)) {
            const hour = parseInt(r.when.split('T')[1]?.split(':')[0] || '12');
            const event = { type: 'reminder', icon: '⏰', text: r.text, time: r.when };
            if (hour < 12) morning.push(event);
            else if (hour < 17) afternoon.push(event);
            else evening.push(event);
          }
        });

        // Process habits (only add if they have preferred_times and aren't already in reminders)
        const habits = Array.isArray(habitsRes.data) ? habitsRes.data : [];
        const reminderTexts = new Set(reminders.map((r: any) => r.text));
        
        habits.forEach((h: any) => {
          // Skip if this habit is already covered by a reminder
          if (reminderTexts.has(h.name) || reminderTexts.has(`Take ${h.name}`)) {
            return;
          }
          
          if (h.active && h.frequency === 'daily') {
            // If habit has preferred_times, use those
            if (h.preferred_times) {
              const times = h.preferred_times.split(',');
              times.forEach((time: string) => {
                const hour = parseInt(time.split(':')[0]);
                const event = { type: 'habit', icon: '✅', text: h.name, time: `${dateStr}T${time}` };
                if (hour < 12) morning.push(event);
                else if (hour < 17) afternoon.push(event);
                else evening.push(event);
              });
            }
          }
        });

        // Process bills due
        const transactions = Array.isArray(financialRes.data) ? financialRes.data : [];
        transactions.forEach((t: any) => {
          if (t.is_recurring && t.due_date === dateStr) {
            const event = { type: 'bill', icon: '💰', text: `${t.bill_name || t.description} - $${Math.abs(t.amount)}` };
            morning.push(event);
          }
        });

        schedule.push({
          day: dayName,
          date: date.getDate(),
          fullDate: dateStr,
          isToday,
          morning,
          afternoon,
          evening,
          morningPreview: morning.slice(0, 3),
          afternoonPreview: afternoon.slice(0, 3),
          eveningPreview: evening.slice(0, 3),
        });
      }

      setWeeklySchedule(schedule);
    } catch (error) {
      console.error('Failed to fetch weekly schedule:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatService.sendMessage(input);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleImageCapture = async (blob: Blob, dataUrl: string) => {
    setShowCamera(false);
    setLoading(true);

    try {
      // Upload image to AI Brain
      const result = await chatService.uploadImage(blob, 'general');

      // Add user message showing the image
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: '📷 Image uploaded',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMessage]);

      // Add AI response
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: result.description || 'Image uploaded successfully!',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to upload image:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: 'Sorry, failed to process the image.',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { icon: '💊', label: 'MEDS', path: '/medications', bgColor: '#2563eb' }, // blue-600
    { icon: '🔔', label: 'REMINDERS', path: '/reminders', bgColor: '#9333ea' }, // purple-600
    { icon: '💰', label: 'FINANCE', path: '/finance', bgColor: '#16a34a' }, // green-600
    { icon: '✓', label: 'HABITS', path: '/habits', bgColor: '#ca8a04' }, // yellow-600
  ];

  return (
    <div className="min-h-screen zombie-gradient p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-zombie-green terminal-glow flex items-center gap-3">
            🧠 KILO AI MEMORY
          </h1>
          {/* Device indicator */}
          <span className="text-xs px-2 py-1 rounded-full bg-dark-border text-zombie-green border border-zombie-green">
            {deviceInfo.type === 'tablet' ? '📱 Tablet' : '💻 Server'}
          </span>
        </div>
        {features.showFullAdminPanel && (
          <Button onClick={() => navigate('/admin')} variant="secondary" size="sm">
            ⚙️ ADMIN
          </Button>
        )}
      </div>

      {/* Real-time updates banner */}
      {realTimeUpdates.length > 0 && (
        <Card className="mb-4 bg-blue-900 border-blue-600">
          <div className="flex items-center gap-2 text-blue-200 p-2">
            <span className="text-xl">🔔</span>
            <span className="text-sm">
              {realTimeUpdates[0].type === 'memory_update' && 'New memory added to your knowledge base'}
              {realTimeUpdates[0].type === 'insight_generated' && 'New AI insight generated'}
              {realTimeUpdates[0].type === 'goal_progress' && 'Goal progress updated'}
            </span>
          </div>
        </Card>
      )}

      {/* Chat Area */}
      <Card className="mb-6 h-[500px] flex flex-col">
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-dark-border">
          <h2 className="text-xl font-semibold text-zombie-green terminal-glow flex items-center gap-2">
            💬 CHAT WITH YOUR AI MEMORY
          </h2>
        </div>

        {/* Messages */}
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto mb-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] p-4 rounded-2xl border-2 ${
                  msg.role === 'user'
                    ? 'bg-zombie-green text-dark-bg border-zombie-green rounded-br-none'
                    : 'bg-dark-border text-zombie-green border-dark-border rounded-bl-none'
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-2xl">{msg.role === 'user' ? '👤' : '🤖'}</span>
                  <p className="text-lg leading-relaxed">{msg.content}</p>
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-dark-border border-2 border-dark-border p-4 rounded-2xl rounded-bl-none">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">🤖</span>
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-zombie-green rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-zombie-green rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-zombie-green rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex flex-col gap-2">
          {/* Voice status indicator */}
          {listening && (
            <div className="flex items-center gap-2 text-sm text-zombie-green animate-pulse">
              <div className="flex gap-1">
                <div className="w-1 h-4 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '0ms' }}></div>
                <div className="w-1 h-6 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '150ms' }}></div>
                <div className="w-1 h-5 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '300ms' }}></div>
                <div className="w-1 h-7 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '450ms' }}></div>
                <div className="w-1 h-4 bg-zombie-green rounded animate-pulse" style={{ animationDelay: '600ms' }}></div>
              </div>
              <span>🎤 Listening...</span>
            </div>
          )}
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder={showVoiceInput ? "Listening..." : "Type your message or use voice..."}
              className="flex-1 px-6 py-4 text-lg rounded-xl border-2 border-dark-border bg-dark-bg text-zombie-green placeholder-zombie-green placeholder-opacity-50 focus:border-zombie-green focus:outline-none"
              disabled={loading}
            />
            <Button
              onClick={toggleVoiceInput}
              disabled={loading}
              size="lg"
              variant={listening ? 'primary' : 'secondary'}
              className={listening ? 'animate-pulse shadow-lg shadow-zombie-green/50' : ''}
            >
              {listening ? '🎙️' : '🎤'}
            </Button>
          {(features.showServerCamera || features.showTabletCamera) && (
            <Button onClick={() => setShowCamera(true)} variant="secondary" size="lg">
              📷
            </Button>
          )}
          <Button onClick={() => {}} variant="secondary" size="lg">
            📎
          </Button>
          </div>
        </div>
      </Card>

      {/* Weekly Schedule Timeline */}
      <Card className="mb-6">
        <h3 className="text-xl font-semibold text-zombie-green mb-4 flex items-center gap-2">
          📅 THIS WEEK'S SCHEDULE
        </h3>
        <div className="grid grid-cols-7 gap-2">
          {weeklySchedule.map((day, idx) => (
            <div 
              key={idx} 
              onClick={() => {
                setSelectedDay(day);
                setShowDayModal(true);
              }}
              className={`border rounded-lg p-3 cursor-pointer transition-all hover:scale-105 ${
                day.isToday 
                  ? 'border-zombie-green bg-zombie-green/10 shadow-lg hover:shadow-zombie-green/50' 
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-500'
              }`}
              style={{ minHeight: 'fit-content' }}
            >
              {/* Day Header */}
              <div className="text-center mb-2 pb-2 border-b border-gray-700">
                <div className={`text-sm font-bold ${day.isToday ? 'text-zombie-green' : 'text-gray-400'}`}>
                  {day.day}
                </div>
                <div className={`text-lg font-bold ${day.isToday ? 'text-zombie-green' : 'text-white'}`}>
                  {day.date}
                </div>
              </div>

              {/* Morning Section */}
              <div className="mb-2">
                <div className="text-xs text-yellow-400 font-semibold mb-1">🌅 Morning</div>
                <div className="space-y-1">
                  {day.morningPreview.length === 0 ? (
                    <div className="text-xs text-gray-600">-</div>
                  ) : (
                    <>
                      {day.morningPreview.map((event: any, i: number) => (
                        <div key={i} className="text-xs text-gray-300 break-words leading-tight">
                          {event.icon} {event.text}
                        </div>
                      ))}
                      {day.morning.length > 3 && (
                        <div className="text-xs text-zombie-green">+{day.morning.length - 3} more</div>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Afternoon Section */}
              <div className="mb-2">
                <div className="text-xs text-orange-400 font-semibold mb-1">☀️ Afternoon</div>
                <div className="space-y-1">
                  {day.afternoonPreview.length === 0 ? (
                    <div className="text-xs text-gray-600">-</div>
                  ) : (
                    <>
                      {day.afternoonPreview.map((event: any, i: number) => (
                        <div key={i} className="text-xs text-gray-300 break-words leading-tight">
                          {event.icon} {event.text}
                        </div>
                      ))}
                      {day.afternoon.length > 3 && (
                        <div className="text-xs text-zombie-green">+{day.afternoon.length - 3} more</div>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Evening Section */}
              <div>
                <div className="text-xs text-blue-400 font-semibold mb-1">🌙 Evening</div>
                <div className="space-y-1">
                  {day.eveningPreview.length === 0 ? (
                    <div className="text-xs text-gray-600">-</div>
                  ) : (
                    <>
                      {day.eveningPreview.map((event: any, i: number) => (
                        <div key={i} className="text-xs text-gray-300 break-words leading-tight">
                          {event.icon} {event.text}
                        </div>
                      ))}
                      {day.evening.length > 3 && (
                        <div className="text-xs text-zombie-green">+{day.evening.length - 3} more</div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Day Detail Modal */}
      {showDayModal && selectedDay && (
        <div 
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setShowDayModal(false)}
        >
          <div 
            className="bg-gray-900 border-2 border-zombie-green rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-700">
              <div>
                <h2 className="text-2xl font-bold text-zombie-green">{selectedDay.day}, {selectedDay.fullDate}</h2>
                <p className="text-gray-400 text-sm">Click outside to close</p>
              </div>
              <button
                onClick={() => setShowDayModal(false)}
                className="text-3xl text-gray-400 hover:text-zombie-green transition-colors"
              >
                ×
              </button>
            </div>

            {/* Morning Events */}
            <div className="mb-6">
              <h3 className="text-xl font-bold text-yellow-400 mb-3 flex items-center gap-2">
                🌅 Morning (5am - 12pm)
              </h3>
              {selectedDay.morning.length === 0 ? (
                <div className="text-gray-500 italic">No events scheduled</div>
              ) : (
                <div className="space-y-2">
                  {selectedDay.morning.map((event: any, i: number) => (
                    <div 
                      key={i} 
                      className="bg-gray-800 border border-gray-700 rounded-lg p-3 hover:border-yellow-400 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{event.icon}</span>
                        <div className="flex-1">
                          <div className="text-white">{event.text}</div>
                          {event.time && (
                            <div className="text-sm text-gray-400">
                              {new Date(event.time).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Afternoon Events */}
            <div className="mb-6">
              <h3 className="text-xl font-bold text-orange-400 mb-3 flex items-center gap-2">
                ☀️ Afternoon (12pm - 5pm)
              </h3>
              {selectedDay.afternoon.length === 0 ? (
                <div className="text-gray-500 italic">No events scheduled</div>
              ) : (
                <div className="space-y-2">
                  {selectedDay.afternoon.map((event: any, i: number) => (
                    <div 
                      key={i} 
                      className="bg-gray-800 border border-gray-700 rounded-lg p-3 hover:border-orange-400 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{event.icon}</span>
                        <div className="flex-1">
                          <div className="text-white">{event.text}</div>
                          {event.time && (
                            <div className="text-sm text-gray-400">
                              {new Date(event.time).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Evening Events */}
            <div>
              <h3 className="text-xl font-bold text-blue-400 mb-3 flex items-center gap-2">
                🌙 Evening (5pm - 11pm)
              </h3>
              {selectedDay.evening.length === 0 ? (
                <div className="text-gray-500 italic">No events scheduled</div>
              ) : (
                <div className="space-y-2">
                  {selectedDay.evening.map((event: any, i: number) => (
                    <div 
                      key={i} 
                      className="bg-gray-800 border border-gray-700 rounded-lg p-3 hover:border-blue-400 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{event.icon}</span>
                        <div className="flex-1">
                          <div className="text-white">{event.text}</div>
                          {event.time && (
                            <div className="text-sm text-gray-400">
                              {new Date(event.time).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Kilo's Insights Widget */}
      {insights.length > 0 && (
        <Card className="mb-6 bg-gradient-to-br from-blue-50 to-purple-50">
          <h3 className="text-xl font-semibold text-blue-800 mb-3 flex items-center gap-2">
            🤖 <span className="terminal-glow">KILO'S INSIGHTS</span>
          </h3>
          <div className="space-y-3">
            {insights.map((insight, idx) => (
              <div key={idx} className={`p-3 rounded-lg border-2 ${
                insight.actionable ? 'bg-green-50 border-green-300' : 'bg-blue-50 border-blue-300'
              }`}>
                <div className="flex items-start gap-3">
                          <span className="text-2xl">
                    {insight.type === 'celebration' && '🎉'}
                    {insight.type === 'warning' && '⚠️'}
                    {insight.type === 'suggestion' && '💡'}
                    {insight.type === 'motivation' && '🚀'}
                    {insight.type === 'reminder' && '🔔'}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800">{insight.title || insight.description}</p>
                    <p className="text-xs text-gray-600 mt-1">{insight.message || insight.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {insight.actionable && (
                        <span className="text-xs bg-green-600 text-white px-2 py-0.5 rounded-full">
                          Actionable
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <div>
        <h3 className="text-xl font-semibold text-zombie-green terminal-glow mb-4">QUICK ACTIONS:</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-4xl mx-auto">
          {quickActions.map((action) => (
            <div
              key={action.path}
              onClick={() => navigate(action.path)}
              className="border-2 border-dark-border rounded-xl shadow-md p-4 cursor-pointer hover:scale-105 hover:shadow-lg hover:border-zombie-green transition-all text-center"
              style={{
                backgroundColor: action.bgColor,
                backgroundImage: 'none'
              }}
            >
              <div className="text-4xl mb-2">{action.icon}</div>
              <div className="text-sm font-semibold text-white">{action.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Camera Modal */}
      {showCamera && (
        <CameraCapture
          onCapture={handleImageCapture}
          onClose={() => setShowCamera(false)}
          type="general"
        />
      )}
    </div>
  );
};

export default Dashboard;
