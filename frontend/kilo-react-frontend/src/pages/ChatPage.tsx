import React, { useState, useRef, useEffect, useCallback } from 'react';
import { chatService } from '../services/chatService';
import { Button } from '../components/shared/Button';

interface ChatMsg {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

// Browser SpeechRecognition API
const SpeechRecognitionAPI =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMsg[]>([
    { id: '1', role: 'ai', content: "Hey Kyle! I'm Kilo, your AI assistant. What's on your mind?", timestamp: new Date() }
  ]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [voiceOn, setVoiceOn]   = useState(true);   // TTS on/off
  const [listening, setListening] = useState(false); // mic active
  const [speaking, setSpeaking]   = useState(false); // TTS playing

  const endRef      = useRef<HTMLDivElement>(null);
  const inputRef    = useRef<HTMLInputElement>(null);
  const audioRef    = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── TTS ──────────────────────────────────────────────────────────────────
  const speak = useCallback(async (text: string) => {
    if (!voiceOn || !text.trim()) return;
    // Stop any currently playing audio
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }

    try {
      // Strip markdown-style symbols that sound bad when spoken
      const clean = text
        .replace(/[#*`_~]/g, '')
        .replace(/\n+/g, ' ')
        .trim()
        .slice(0, 500); // cap length so it doesn't read essays

      const url = `/api/voice/tts?text=${encodeURIComponent(clean)}&voice=kilo`;
      const audio = new Audio(url);
      audioRef.current = audio;
      setSpeaking(true);
      audio.onended = () => { setSpeaking(false); audioRef.current = null; };
      audio.onerror = () => { setSpeaking(false); audioRef.current = null; };
      await audio.play();
    } catch (e) {
      setSpeaking(false);
    }
  }, [voiceOn]);

  const stopSpeaking = () => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    setSpeaking(false);
  };

  // ── STT ──────────────────────────────────────────────────────────────────
  const startListening = useCallback(() => {
    if (!SpeechRecognitionAPI) {
      alert('Speech recognition not supported in this browser. Try Chrome or Edge.');
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognitionRef.current = recognition;

    recognition.onstart  = () => setListening(true);
    recognition.onend    = () => setListening(false);
    recognition.onerror  = () => setListening(false);
    recognition.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript;
      setInput(transcript);
      // Auto-send after mic input
      setTimeout(() => {
        setInput('');
        sendText(transcript);
      }, 300);
    };

    recognition.start();
  }, [listening]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Send message ──────────────────────────────────────────────────────────
  const sendText = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMsg = {
      id: Date.now().toString(), role: 'user', content: trimmed, timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await chatService.sendMessage(trimmed);
      const aiMsg: ChatMsg = {
        id: (Date.now() + 1).toString(), role: 'ai', content: response, timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMsg]);
      speak(response);
    } catch (err: any) {
      const errMsg = `Sorry, I ran into an error: ${err.message || 'Failed to get response'}`;
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(), role: 'ai', content: errMsg, timestamp: new Date()
      }]);
    }
    setLoading(false);
    inputRef.current?.focus();
  };

  const send = () => {
    sendText(input);
    setInput('');
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">

      {/* Toolbar */}
      <div className="flex items-center justify-end gap-2 px-4 pt-2 pb-1 border-b border-dark-border">
        {/* Voice toggle */}
        <button
          onClick={() => { if (voiceOn) stopSpeaking(); setVoiceOn(v => !v); }}
          title={voiceOn ? 'Mute Kilo' : 'Unmute Kilo'}
          className={`p-2 rounded-lg text-sm transition-colors ${
            voiceOn ? 'text-zombie-green bg-zombie-green/10' : 'text-dark-text/40 bg-dark-card'
          }`}
        >
          {speaking ? '🔊' : voiceOn ? '🔈' : '🔇'}
        </button>

        {/* Status label */}
        <span className="text-xs text-dark-text/40">
          {speaking ? 'Kilo is speaking…' : voiceOn ? 'Voice on' : 'Voice off'}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
              msg.role === 'user'
                ? 'bg-zombie-green/20 border border-zombie-green/40 text-dark-text'
                : 'bg-dark-card border border-dark-border text-dark-text'
            }`}>
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              <p className="text-xs text-dark-text/40 mt-1">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-dark-card border border-dark-border rounded-lg px-4 py-2">
              <p className="text-sm text-zombie-green animate-pulse">Kilo is thinking…</p>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-dark-border p-4">
        <div className="flex gap-2">
          {/* Mic button */}
          <button
            onClick={startListening}
            disabled={loading}
            title={listening ? 'Stop listening' : 'Speak to Kilo'}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
              listening
                ? 'bg-red-500/20 border border-red-500/60 text-red-400 animate-pulse'
                : 'bg-dark-card border border-dark-border text-dark-text/60 hover:border-zombie-green/40 hover:text-zombie-green'
            }`}
          >
            {listening ? '⏹ Stop' : '🎤'}
          </button>

          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder={listening ? 'Listening…' : 'Talk to Kilo…'}
            className="flex-1 bg-dark-card border border-dark-border rounded-lg px-4 py-2 text-dark-text text-sm placeholder-dark-text/40 focus:border-zombie-green/60 focus:outline-none"
            disabled={loading || listening}
          />
          <Button variant="primary" size="sm" onClick={send} disabled={loading || !input.trim()}>
            Send
          </Button>
        </div>
        {!SpeechRecognitionAPI && (
          <p className="text-xs text-dark-text/30 mt-1">
            Mic requires Chrome or Edge browser
          </p>
        )}
      </div>
    </div>
  );
};

export default ChatPage;
