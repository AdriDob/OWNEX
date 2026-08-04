import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import { useStore } from '@stores/useStore';
import { Notification } from '@types';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
  }),
});

export const notificationService = {
  async registerForPushNotifications(): Promise<string | null> {
    if (!Device.isDevice) {
      console.log('[Notifications] Must use physical device for push notifications');
      return null;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.log('[Notifications] Permission not granted');
      return null;
    }

    try {
      const token = (await Notifications.getExpoPushTokenAsync({
        projectId: process.env.EXPO_PUBLIC_PROJECT_ID,
      })).data;
      
      console.log('[Notifications] Push token:', token);
      
      // Send token to backend
      await this.sendTokenToBackend(token);
      
      return token;
    } catch (e) {
      console.error('[Notifications] Error getting push token:', e);
      return null;
    }
  },

  async sendTokenToBackend(token: string) {
    try {
      const { auth } = useStore.getState();
      if (auth.token) {
        await fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/notifications/token`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${auth.token}`,
          },
          body: JSON.stringify({ token, platform: Platform.OS }),
        });
      }
    } catch (e) {
      console.error('[Notifications] Failed to send token to backend:', e);
    }
  },

  async scheduleLocalNotification(notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: notification.title,
        body: notification.message,
        data: {
          type: notification.type,
          actionUrl: notification.actionUrl,
          actionLabel: notification.actionLabel,
          metadata: notification.metadata,
        },
        sound: notification.priority === 'critical' ? 'critical' : 'default',
        priority: notification.priority === 'critical' ? 'high' : 'normal',
      },
      trigger: null, // Show immediately
    });
  },

  async showLocalNotification(title: string, body: string, data?: Record<string, unknown>) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        data: data || {},
        sound: 'default',
      },
      trigger: null,
    });
  },

  addNotificationListener(
    onNotification: (notification: Notifications.Notification) => void,
    onResponse: (response: Notifications.NotificationResponse) => void
  ) {
    const listener1 = Notifications.addNotificationReceivedListener(onNotification);
    const listener2 = Notifications.addNotificationResponseReceivedListener(onResponse);
    
    return () => {
      Notifications.removeNotificationSubscription(listener1);
      Notifications.removeNotificationSubscription(listener2);
    };
  },

  async setBadgeCount(count: number) {
    await Notifications.setBadgeCountAsync(count);
  },

  async clearBadge() {
    await Notifications.setBadgeCountAsync(0);
  },

  async cancelAllScheduled() {
    await Notifications.cancelAllScheduledNotificationsAsync();
  },

  // Critical alert (bypasses Do Not Disturb on iOS)
  async showCriticalAlert(title: string, body: string) {
    if (Platform.OS === 'ios') {
      await Notifications.scheduleNotificationAsync({
        content: {
          title,
          body,
          sound: 'critical',
          priority: 'high',
          interruptionLevel: 'critical',
        },
        trigger: null,
      });
    } else {
      await this.showLocalNotification(title, body);
    }
  },

  // Channel configuration for Android
  async createChannels() {
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('critical', {
        name: 'Critical Alerts',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#ef4444',
        sound: 'critical',
        enableVibrate: true,
        enableLights: true,
      });

      await Notifications.setNotificationChannelAsync('approvals', {
        name: 'Approvals Required',
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 100, 100],
        lightColor: '#f59e0b',
        sound: 'default',
        enableVibrate: true,
      });

      await Notifications.setNotificationChannelAsync('agents', {
        name: 'Agent Updates',
        importance: Notifications.AndroidImportance.DEFAULT,
        sound: 'default',
        enableVibrate: false,
      });

      await Notifications.setNotificationChannelAsync('workflows', {
        name: 'Workflow Updates',
        importance: Notifications.AndroidImportance.DEFAULT,
        sound: 'default',
        enableVibrate: false,
      });

      await Notifications.setNotificationChannelAsync('findings', {
        name: 'New Findings',
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 200, 100, 200],
        lightColor: '#00d4ff',
        sound: 'default',
        enableVibrate: true,
      });
    }
  },
};

// Helper to convert backend notification to local notification
export const convertToLocalNotification = (notification: Notification) => {
  return {
    title: notification.title,
    body: notification.message,
    data: {
      type: notification.type,
      actionUrl: notification.actionUrl,
      actionLabel: notification.actionLabel,
      metadata: notification.metadata,
      notificationId: notification.id,
    },
  };
};