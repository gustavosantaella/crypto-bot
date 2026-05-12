import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private socket?: WebSocket;
  private messageSubject = new Subject<any>();
  private wsUrl = environment.wsUrl;

  constructor() {
    this.connect();
  }

  private connect() {
    this.socket = new WebSocket(this.wsUrl);

    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.messageSubject.next(data);
    };

    this.socket.onclose = (event) => {
      console.log('WS Connection closed. Reconnecting in 3s...', event);
      setTimeout(() => this.connect(), 3000);
    };

    this.socket.onerror = (error) => {
      console.error('WS Error:', error);
      this.socket?.close();
    };
  }

  getMessages(): Observable<any> {
    return this.messageSubject.asObservable();
  }
}
