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
          const newNotifications = data.notifications || [];
          
          // Add only new notifications (not already in state)
          const existingIds = new Set(notifications.map(n => n.id));
          const toAdd = newNotifications.filter((n: NotificationData) => !existingIds.has(n.id));
          
          if (toAdd.length > 0) {
            setNotifications(prev => [...prev, ...toAdd]);
          }
        }
      } catch (error) {
        console.error('Failed to fetch notifications:', error);
      }
    };

    // Poll every 30 seconds
    const interval = setInterval(pollNotifications, 30000);
    pollNotifications(); // Initial fetch

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
