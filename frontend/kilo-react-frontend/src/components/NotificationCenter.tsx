import React, { useState, useEffect } from 'react';
import { InteractiveNotification } from './InteractiveNotification';

interface NotificationData {
  id: number;
  channel: string;
  payload_json: string;
  created_at: string;
}

export const NotificationCenter: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationData[]>([]);

  useEffect(() => {
    const pollNotifications = async () => {
      try {
        const response = await fetch(
          `${process.env.REACT_APP_API_BASE_URL || ''}/api/reminder/notifications/pending`
        );
        if (response.ok) {
          const data = await response.json();
          const rawList: any[] = Array.isArray(data) ? data : (data.notifications || []);

          const transformed: NotificationData[] = rawList.map((item: any) => {
            const msg = (item.message || item.text || '').toLowerCase();
            let channel = 'reminder';
            if (msg.includes('med') || msg.includes('pill') || msg.includes('effexor') ||
                msg.includes('adderall') || msg.includes('buspirone') || msg.includes('💊')) {
              channel = 'med';
            } else if (msg.includes('habit')) {
              channel = 'habit';
            }
            return {
              id: item.id,
              channel,
              payload_json: JSON.stringify({
                text: item.message || item.text || 'Reminder',
                when: item.timestamp || item.when || item.created_at || '',
              }),
              created_at: item.timestamp || item.created_at || new Date().toISOString(),
            };
          });

          const existingIds = new Set(notifications.map(n => n.id));
          const toAdd = transformed.filter((n: NotificationData) => !existingIds.has(n.id));
          if (toAdd.length > 0) {
            setNotifications(prev => [...prev, ...toAdd]);
          }
        }
      } catch (error) {
        console.error('Failed to fetch notifications:', error);
      }
    };

    const interval = setInterval(pollNotifications, 30000);
    pollNotifications();
    return () => clearInterval(interval);
  }, [notifications]);

  const dismissNotification = (id: number) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  return (
    <div className="fixed top-4 right-4 z-50 max-h-screen overflow-y-auto">
      {notifications.map(notification => (
        <InteractiveNotification
          key={notification.id}
          notification={notification}
          onDismiss={dismissNotification}
        />
      ))}
    </div>
  );
};
