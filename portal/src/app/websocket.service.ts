import { Injectable } from '@angular/core';
import { Subject, Observable, BehaviorSubject } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private socket?: WebSocket;
  private messageSubject = new Subject<any>();
  private connectionState = new BehaviorSubject<boolean>(false);
  private wsUrl = environment.wsUrl;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;  // Max 30s between reconnects
  private reconnectTimer: any;
  private isIntentionalClose = false;

  constructor() {
    this.connect();
  }

  private connect() {
    // Prevent multiple simultaneous connections
    if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)) {
      return;
    }

    try {
      this.socket = new WebSocket(this.wsUrl);

      this.socket.onopen = () => {
        console.log('✅ WS Connected');
        this.connectionState.next(true);
        this.reconnectAttempts = 0;  // Reset backoff on successful connect
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.messageSubject.next(data);
        } catch (e) {
          console.warn('WS: Failed to parse message:', e);
        }
      };

      this.socket.onclose = (event) => {
        this.connectionState.next(false);

        if (!this.isIntentionalClose) {
          this.reconnectAttempts++;
          // Exponential backoff: 1s, 2s, 4s, 8s, ... up to maxReconnectDelay
          const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay);
          console.log(`🔄 WS closed (code: ${event.code}). Reconnecting in ${delay / 1000}s... (attempt ${this.reconnectAttempts})`);

          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = setTimeout(() => this.connect(), delay);
        }
      };

      this.socket.onerror = (error) => {
        console.error('❌ WS Error:', error);
        // Don't close here — let onclose handle reconnection
      };
    } catch (e) {
      console.error('WS: Failed to create connection:', e);
      // Schedule reconnect even if constructor fails
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
    }
  }

  getMessages(): Observable<any> {
    return this.messageSubject.asObservable();
  }

  /** Observable that emits true when connected, false when disconnected */
  getConnectionState(): Observable<boolean> {
    return this.connectionState.asObservable();
  }

  /** Whether the WebSocket is currently connected */
  get isConnected(): boolean {
    return this.connectionState.value;
  }

  /** Force a reconnection (e.g., when switching tabs back) */
  forceReconnect() {
    if (this.socket) {
      this.isIntentionalClose = true;
      this.socket.close();
      this.isIntentionalClose = false;
    }
    this.reconnectAttempts = 0;
    this.connect();
  }
}
