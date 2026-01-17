import React, { useState, useEffect } from 'react';
import { X, Check, Clock, XCircle } from 'lucide-react';

interface NotificationData {
  id: number;
  channel: string;
  payload_json: string;
  created_at: string;
}

interface InteractiveNotificationProps {
  notification: NotificationData;
  onDismiss: (id: number) => void;
}

export const InteractiveNotification: React.FC<InteractiveNotificationProps> = ({
  notification,
  onDismiss,
}) => {
  const [showSnoozeOptions, setShowSnoozeOptions] = useState(false);
  const [notes, setNotes] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const payload = JSON.parse(notification.payload_json);
  const reminderText = payload.text || 'Reminder';
  const reminderTime = payload.when || notification.created_at;

  const typeColors = {
    reminder: 'bg-blue-500',
    habit: 'bg-purple-500',
    med: 'bg-green-500',
    info: 'bg-gray-500',
  };

  const typeIcons = {
    reminder: '⏰',
    habit: '✅',
    med: '💊',
    info: 'ℹ️',
  };

  const color = typeColors[notification.channel as keyof typeof typeColors] || 'bg-gray-500';
  const icon = typeIcons[notification.channel as keyof typeof typeIcons] || 'ℹ️';

  const handleAction = async (action: 'completed' | 'skipped' | 'snoozed', snoozeMinutes?: number) => {
    setIsProcessing(true);
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL || ''}/api/reminder/notifications/${notification.id}/confirm`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            snooze_minutes: snoozeMinutes,
            notes: notes.trim() || undefined,
          }),
        }
      );

      if (response.ok) {
        onDismiss(notification.id);
      } else {
        console.error('Failed to confirm notification');
      }
    } catch (error) {
      console.error('Error confirming notification:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDismiss = async () => {
    setIsProcessing(true);
    try {
      await fetch(
        `${process.env.REACT_APP_API_BASE_URL || ''}/api/reminder/notifications/${notification.id}/mark_read`,
        { method: 'POST' }
      );
      onDismiss(notification.id);
    } catch (error) {
      console.error('Error dismissing notification:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className={`${color} rounded-lg shadow-2xl p-5 mb-3 min-w-[350px] max-w-[450px] animate-slide-in`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3 flex-1">
          <span className="text-3xl">{icon}</span>
          <div className="flex-1">
            <p className="text-white font-bold text-lg mb-1">{reminderText}</p>
            <p className="text-white/70 text-xs">
              {new Date(reminderTime).toLocaleString()}
            </p>
          </div>
        </div>
        <button
          onClick={handleDismiss}
          disabled={isProcessing}
          className="text-white bg-white/20 hover:bg-white/40 rounded-full p-2 transition-all flex-shrink-0"
          aria-label="Dismiss without action"
          title="Dismiss (no record)"
        >
          <X size={20} strokeWidth={3} />
        </button>
      </div>

      {/* Optional Notes */}
      <input
        type="text"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Add notes (optional)..."
        className="w-full bg-white/20 text-white placeholder-white/60 rounded px-3 py-2 mb-3 text-sm"
        disabled={isProcessing}
      />

      {/* Action Buttons */}
      {!showSnoozeOptions ? (
        <div className="flex gap-2">
          <button
            onClick={() => handleAction('completed')}
            disabled={isProcessing}
            className="flex-1 bg-white/90 hover:bg-white text-gray-800 font-semibold py-2 px-3 rounded flex items-center justify-center gap-2 transition-all"
            title="Mark as completed"
          >
            <Check size={18} />
            <span>Done</span>
          </button>
          <button
            onClick={() => setShowSnoozeOptions(true)}
            disabled={isProcessing}
            className="flex-1 bg-white/70 hover:bg-white/90 text-gray-800 font-semibold py-2 px-3 rounded flex items-center justify-center gap-2 transition-all"
            title="Snooze reminder"
          >
            <Clock size={18} />
            <span>Snooze</span>
          </button>
          <button
            onClick={() => handleAction('skipped')}
            disabled={isProcessing}
            className="flex-1 bg-white/50 hover:bg-white/70 text-gray-800 font-semibold py-2 px-3 rounded flex items-center justify-center gap-2 transition-all"
            title="Skip this time"
          >
            <XCircle size={18} />
            <span>Skip</span>
          </button>
        </div>
      ) : (
        <div>
          <div className="grid grid-cols-3 gap-2 mb-2">
            <button
              onClick={() => handleAction('snoozed', 5)}
              disabled={isProcessing}
              className="bg-white/80 hover:bg-white text-gray-800 font-semibold py-2 px-2 rounded text-sm transition-all"
            >
              5 min
            </button>
            <button
              onClick={() => handleAction('snoozed', 15)}
              disabled={isProcessing}
              className="bg-white/80 hover:bg-white text-gray-800 font-semibold py-2 px-2 rounded text-sm transition-all"
            >
              15 min
            </button>
            <button
              onClick={() => handleAction('snoozed', 30)}
              disabled={isProcessing}
              className="bg-white/80 hover:bg-white text-gray-800 font-semibold py-2 px-2 rounded text-sm transition-all"
            >
              30 min
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleAction('snoozed', 60)}
              disabled={isProcessing}
              className="bg-white/80 hover:bg-white text-gray-800 font-semibold py-2 px-2 rounded text-sm transition-all"
            >
              1 hour
            </button>
            <button
              onClick={() => setShowSnoozeOptions(false)}
              disabled={isProcessing}
              className="bg-white/50 hover:bg-white/70 text-gray-800 font-semibold py-2 px-2 rounded text-sm transition-all"
            >
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InteractiveNotification;
