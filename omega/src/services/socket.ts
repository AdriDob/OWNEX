import { apiService } from './api';
import { WSMessage, WSEvent } from '@types';

type WSMessageHandler = (message: WSMessage) => void;
type WSEventHandler = (event: WSEvent) => void;

class SocketService {
  private ws: WebSocket | null = null;
  private url: string = '';
  private token: string = '';
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;
  private reconnectDelay: number = 1000;
  private messageHandlers: Set<WSMessageHandler> = new Set();
  private eventHandlers: Map<string, Set<WSEventHandler>> = new Map();
  private pingInterval: NodeJS.Timeout | null = null;
  private isConnecting: boolean = false;
  private shouldReconnect: boolean = true;

  connect(token: string, baseUrl?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      if (this.isConnecting) {
        // Wait for existing connection attempt
        const checkConnection = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            clearInterval(checkConnection);
            resolve();
          } else if (this.ws?.readyState === WebSocket.CLOSED) {
            clearInterval(checkConnection);
            reject(new Error('Connection failed'));
          }
        }, 100);
        return;
      }

      this.token = token;
      this.url = baseUrl || process.env.EXPO_PUBLIC_WS_URL || 'wss://api.ownex.local/ws';
      this.isConnecting = true;
      this.shouldReconnect = true;

      try {
        this.ws = new WebSocket(`${this.url}?token=${encodeURIComponent(token)}`);
        
        this.ws.onopen = () => {
          console.log('[Socket] Connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startPing();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (e) {
            console.error('[Socket] Parse error:', e);
          }
        };

        this.ws.onclose = (event) => {
          console.log('[Socket] Closed:', event.code, event.reason);
          this.isConnecting = false;
          this.stopPing();
          if (this.shouldReconnect && !event.wasClean) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('[Socket] Error:', error);
          this.isConnecting = false;
          reject(error);
        };
      } catch (e) {
        this.isConnecting = false;
        reject(e);
      }
    });
  }

  private handleMessage(message: WSMessage) {
    // Notify general handlers
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (e) {
        console.error('[Socket] Handler error:', e);
      }
    });

    // Notify event-specific handlers
    if (message.type.startsWith('event:')) {
      const eventName = message.type.replace('event:', '');
      const handlers = this.eventHandlers.get(eventName);
      if (handlers) {
        const event: WSEvent = {
          event: eventName,
          data: message.payload,
          priority: (message.payload as any)?.priority || 'medium',
        };
        handlers.forEach(handler => {
          try {
            handler(event);
          } catch (e) {
            console.error('[Socket] Event handler error:', e);
          }
        });
      }
    }
  }

  private startPing() {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping', payload: {}, timestamp: Date.now(), id: `ping-${Date.now()}` });
      }
    }, 30000);
  }

  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[Socket] Max reconnect attempts reached');
      return;
    }

    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    
    console.log(`[Socket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      if (this.shouldReconnect && this.token) {
        this.connect(this.token).catch(() => {});
      }
    }, delay);
  }

  send(message: WSMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  subscribe(handler: WSMessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onEvent(eventName: string, handler: WSEventHandler) {
    if (!this.eventHandlers.has(eventName)) {
      this.eventHandlers.set(eventName, new Set());
    }
    this.eventHandlers.get(eventName)!.add(handler);
    return () => this.eventHandlers.get(eventName)?.delete(handler);
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopPing();
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.messageHandlers.clear();
    this.eventHandlers.clear();
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

export const socketService = new SocketService();