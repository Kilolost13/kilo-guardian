import React, { useState, useEffect } from "react";

interface MeshNode {
  id: string;
  name: string;
  lastSeen: string;
  battery: number;
  snr: number;
  distance?: number;
}

interface MeshMessage {
  from: string;
  text: string;
  timestamp: string;
}

export default function Meshtastic() {
  const [nodes, setNodes] = useState<MeshNode[]>([]);
  const [messages, setMessages] = useState<MeshMessage[]>([]);
  const [newMessage, setNewMessage] = useState("");

  useEffect(() => {
    fetchNodes();
    fetchMessages();
    const interval = setInterval(() => {
      fetchNodes();
      fetchMessages();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchNodes = async () => {
    try {
      const res = await fetch("/api/meshtastic/nodes");
      if (res.ok) {
        const data = await res.json();
        setNodes(data.nodes || []);
      }
    } catch (err) {
      console.error("Failed to fetch nodes:", err);
    }
  };

  const fetchMessages = async () => {
    try {
      const res = await fetch("/api/meshtastic/messages");
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
      }
    } catch (err) {
      console.error("Failed to fetch messages:", err);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    try {
      await fetch("/api/meshtastic/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: newMessage })
      });
      setNewMessage("");
      fetchMessages();
    } catch (err) {
      console.error("Failed to send message:", err);
    }
  };

  return (
    <div className="p-6 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-neon mb-8 font-mono uppercase tracking-wider">
          📡 Meshtastic Network
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-black border-2 border-neon p-6 rounded">
            <h2 className="text-2xl font-bold text-neon mb-4">Network Nodes ({nodes.length})</h2>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {nodes.map((node) => (
                <div key={node.id} className="bg-gray-900 border border-neon-dim p-4 rounded">
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-bold text-white">{node.name}</div>
                    <div className="text-sm text-gray-400">{node.lastSeen}</div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <span className="text-gray-400">Battery:</span>
                      <span className="text-neon ml-2">{node.battery}%</span>
                    </div>
                    <div>
                      <span className="text-gray-400">SNR:</span>
                      <span className="text-neon ml-2">{node.snr} dB</span>
                    </div>
                    {node.distance && (
                      <div>
                        <span className="text-gray-400">Distance:</span>
                        <span className="text-neon ml-2">{node.distance}m</span>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-2 font-mono">{node.id}</div>
                </div>
              ))}
              {nodes.length === 0 && (
                <div className="text-gray-500 text-center py-8">No nodes detected</div>
              )}
            </div>
          </div>

          <div className="bg-black border-2 border-neon p-6 rounded flex flex-col">
            <h2 className="text-2xl font-bold text-neon mb-4">Messages</h2>
            <div className="flex-1 space-y-2 max-h-80 overflow-y-auto mb-4">
              {messages.map((msg, idx) => (
                <div key={idx} className="bg-gray-900 border border-neon-dim p-3 rounded">
                  <div className="flex justify-between items-start mb-1">
                    <div className="font-bold text-white text-sm">{msg.from}</div>
                    <div className="text-xs text-gray-400">{msg.timestamp}</div>
                  </div>
                  <div className="text-gray-300">{msg.text}</div>
                </div>
              ))}
              {messages.length === 0 && (
                <div className="text-gray-500 text-center py-8">No messages</div>
              )}
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Type a message..."
                className="flex-1 bg-gray-900 border border-neon-dim text-white px-4 py-2 rounded focus:outline-none focus:border-neon"
              />
              <button
                onClick={sendMessage}
                className="bg-neon text-black px-6 py-2 rounded font-bold hover:bg-white transition-colors"
              >
                SEND
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
