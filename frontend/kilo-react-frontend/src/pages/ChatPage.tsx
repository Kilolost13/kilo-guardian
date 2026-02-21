import React, { useState, useRef, useEffect } from 'react';
import { chatService } from '../services/chatService';
import { Button } from '../components/shared/Button';

interface ChatMsg {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMsg[]>([
    { id: '1', role: 'ai', content: "Hey Kyle! I'm Kilo, your AI assistant. What's on your mind?", timestamp: new Date() }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMsg = { id: Date.now().toString(), role: 'user', content: text, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatService.sendMessage(text);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response,
        timestamp: new Date(),
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: `Error: ${err.message || 'Failed to get response'}`,
        timestamp: new Date(),
      }]);
    }
    setLoading(false);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
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
              <p className="text-sm text-zombie-green animate-pulse">Kilo is thinking...</p>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-dark-border p-4">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Talk to Kilo..."
            className="flex-1 bg-dark-card border border-dark-border rounded-lg px-4 py-2 text-dark-text text-sm placeholder-dark-text/40 focus:border-zombie-green/60 focus:outline-none"
            disabled={loading}
          />
          <Button variant="primary" size="sm" onClick={send} disabled={loading || !input.trim()}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
