/**
 * Offline Queue - IndexedDB-based mutation queue for offline-first support
 * Uses native IndexedDB (no external dependencies)
 */

export interface QueuedMutation {
  id: string;
  entityType: string;
  entityId: string;
  operation: 'create' | 'update' | 'delete';
  payload: Record<string, unknown>;
  timestamp: number;
  retries: number;
  endpoint: string;
  method: 'POST' | 'PUT' | 'DELETE' | 'PATCH';
}

export interface OfflineQueueOptions {
  dbName: string;
  storeName: string;
  maxRetries: number;
  maxAge: number; // milliseconds
}

const DEFAULT_OPTIONS: OfflineQueueOptions = {
  dbName: 'ownex-offline',
  storeName: 'mutations',
  maxRetries: 3,
  maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
};

class OfflineQueue {
  private db: IDBDatabase | null = null;
  private options: OfflineQueueOptions;
  private readyPromise: Promise<void> | null = null;

  constructor(options: Partial<OfflineQueueOptions> = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.readyPromise = this.initDB();
  }

  private async initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.options.dbName, 1);

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.options.storeName)) {
          const store = db.createObjectStore(this.options.storeName, { keyPath: 'id' });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('entityType', 'entityType', { unique: false });
        }
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  async ensureReady(): Promise<void> {
    if (this.readyPromise) {
      await this.readyPromise;
    }
  }

  async enqueue(mutation: Omit<QueuedMutation, 'id' | 'timestamp' | 'retries'>): Promise<string> {
    await this.ensureReady();
    
    const id = crypto.randomUUID();
    const mutationRecord: QueuedMutation = {
      ...mutation,
      id,
      timestamp: Date.now(),
      retries: 0,
    };

    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      const transaction = this.db.transaction([this.options.storeName], 'readwrite');
      const store = transaction.objectStore(this.options.storeName);
      const request = store.add({
        ...mutationRecord,
        timestamp: mutationRecord.timestamp,
      });

      request.onsuccess = () => resolve(id);
      request.onerror = () => reject(request.error);
    });
  }

  async getAll(): Promise<QueuedMutation[]> {
    await this.ensureReady();
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve([]);
        return;
      }

      const transaction = this.db.transaction([this.options.storeName], 'readonly');
      const store = transaction.objectStore(this.options.storeName);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  async getPendingCount(): Promise<number> {
    const all = await this.getAll();
    return all.length;
  }

  async remove(id: string): Promise<void> {
    await this.ensureReady();
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve();
        return;
      }

      const transaction = this.db.transaction([this.options.storeName], 'readwrite');
      const store = transaction.objectStore(this.options.storeName);
      const request = store.delete(id);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async updateRetries(id: string, retries: number): Promise<void> {
    await this.ensureReady();
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve();
        return;
      }

      const transaction = this.db.transaction([this.options.storeName], 'readwrite');
      const store = transaction.objectStore(this.options.storeName);
      const getRequest = store.get(id);

      getRequest.onsuccess = () => {
        const mutation = getRequest.result;
        if (mutation) {
          mutation.retries = retries;
          const putRequest = store.put(mutation);
          putRequest.onsuccess = () => resolve();
          putRequest.onerror = () => reject(putRequest.error);
        } else {
          resolve();
        }
      };
      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  async clearOld(maxAge: number = DEFAULT_OPTIONS.maxAge): Promise<number> {
    await this.ensureReady();
    
    const all = await this.getAll();
    const now = Date.now();
    let removed = 0;

    for (const mutation of all) {
      if (now - mutation.timestamp > maxAge) {
        await this.remove(mutation.id);
        removed++;
      }
    }

    return removed;
  }

  async clearAll(): Promise<void> {
    await this.ensureReady();
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve();
        return;
      }

      const transaction = this.db.transaction([this.options.storeName], 'readwrite');
      const store = transaction.objectStore(this.options.storeName);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
}

// Singleton instance
let offlineQueueInstance: OfflineQueue | null = null;

export function getOfflineQueue(options?: Partial<OfflineQueueOptions>): OfflineQueue {
  if (!offlineQueueInstance) {
    offlineQueueInstance = new OfflineQueue(options);
  }
  return offlineQueueInstance;
}

export function resetOfflineQueue(): void {
  offlineQueueInstance = null;
}

/**
 * Service Worker Registration & Communication
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    console.warn('[Offline] Service Worker not supported');
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register('/service-worker.js', {
      scope: '/',
    });

    // Handle updates
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      if (newWorker) {
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New version available
            console.log('[SW] New version available');
            // Could dispatch custom event for UI notification
            window.dispatchEvent(new CustomEvent('sw-update-available'));
          }
        });
      }
    });

    // Listen for messages from SW
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'SYNC_COMPLETE') {
        window.dispatchEvent(new CustomEvent('offline-sync-complete', { detail: event.data }));
      }
      if (event.data?.type === 'OFFLINE_MUTATION_ACK') {
        window.dispatchEvent(new CustomEvent('offline-mutation-ack', { detail: event.data }));
      }
    });

    console.log('[SW] Service Worker registered:', registration.scope);
    return registration;
  } catch (error) {
    console.error('[SW] Registration failed:', error);
    return null;
  }
}

export async function unregisterServiceWorker(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) return false;
  
  const registration = await navigator.serviceWorker.getRegistration();
  if (registration) {
    return registration.unregister();
  }
  return false;
}

/**
 * Network Status Detection
 */
export function isOnline(): boolean {
  return navigator.onLine;
}

export function onOnlineChange(callback: (online: boolean) => void): () => void {
  const handler = () => callback(navigator.onLine);
  window.addEventListener('online', handler);
  window.addEventListener('offline', handler);
  return () => {
    window.removeEventListener('online', handler);
    window.removeEventListener('offline', handler);
  };
}

/**
 * Background Sync Integration (for when browser supports it)
 */
export async function registerBackgroundSync(tag: string): Promise<boolean> {
  if (!('serviceWorker' in navigator) || !('sync' in window.ServiceWorkerRegistration.prototype)) {
    console.warn('[Background Sync] Not supported');
    return false;
  }

  try {
    const registration = await navigator.serviceWorker.ready;
    await (registration as any).sync.register(tag);
    console.log('[Background Sync] Registered:', tag);
    return true;
  } catch (error) {
    console.error('[Background Sync] Registration failed:', error);
    return false;
  }
}

/**
 * Queue a mutation for offline execution with automatic retry
 */
export async function queueOfflineMutation(
  mutation: Omit<QueuedMutation, 'id' | 'timestamp' | 'retries'>,
  queue: OfflineQueue
): Promise<string> {
  return queue.enqueue(mutation);
}

/**
 * Process offline queue when online
 */
export async function processOfflineQueue(
  queue: ReturnType<typeof import('./offline').getOfflineQueue>,
  apiCall: (mutation: any) => Promise<Response>
): Promise<{ processed: number; failed: number }> {
  const mutations = await queue.getAll();
  let processed = 0;
  let failed = 0;

  for (const mutation of mutations) {
    try {
      const response = await apiCall(mutation);
      if (response.ok) {
        await queue.remove(mutation.id);
        processed++;
      } else {
        const retries = mutation.retries + 1;
        if (retries >= 3) {
          failed++;
          // Don't remove - keep for manual review
        } else {
          // Update retries count - would need update method
        }
      }
    } catch (error) {
      console.error('[Offline Queue] Failed to process mutation:', error);
      failed++;
    }
  }

  return { processed, failed };
}