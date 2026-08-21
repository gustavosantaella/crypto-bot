import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface ServerEvent {
  type: string;
  data: unknown;
}

/**
 * Conexión SSE con la API (`GET /api/events`).
 *
 * El backend publica eventos cuando se registra una compra/venta/cancelación
 * de una transacción; aquí se exponen como un Observable para que los
 * componentes recarguen sus datos en tiempo real.
 *
 * `EventSource` se reconecta automáticamente si la conexión se cae.
 */
@Injectable({ providedIn: 'root' })
export class EventService {
  private readonly events = new Subject<ServerEvent>();
  private readonly connectionState = new Subject<boolean>();
  private readonly source = new EventSource(`${environment.apiUrl}/events`);

  /** Emite con cada evento de transacción (created/updated/canceled). */
  readonly changes$ = this.events.asObservable();
  /** Estado de la conexión SSE (true = conectado, false = desconectado). */
  readonly connection$ = this.connectionState.asObservable();

  constructor() {
    this.source.onopen = () => {
      console.info('[SSE] conectado al stream de eventos');
      this.connectionState.next(true);
    };
    this.source.onerror = () => {
      console.warn('[SSE] desconectado; EventSource reintentará...');
      this.connectionState.next(false);
    };
    this.source.addEventListener('transaction.created', (e) => this.emit('transaction.created', e));
    this.source.addEventListener('transaction.updated', (e) => this.emit('transaction.updated', e));
    this.source.addEventListener('transaction.canceled', (e) => this.emit('transaction.canceled', e));
  }

  private emit(type: string, event: MessageEvent): void {
    try {
      this.events.next({ type, data: JSON.parse(event.data) });
    } catch (err) {
      console.warn('[SSE] evento inválido', err);
    }
  }
}
