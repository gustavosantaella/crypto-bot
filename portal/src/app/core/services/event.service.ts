import { Injectable } from '@angular/core';
import { filter, Observable, Subject } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface ServerEvent {
  type: string;
  data: unknown;
}

/**
 * Conexión SSE con la API (`GET /api/events`).
 *
 * El backend publica eventos cuando se registra una compra/venta/cancelación
 * y también el precio en vivo de Binance (evento ``price``, cada ~2s).
 *
 * `EventSource` se reconecta automáticamente si la conexión se cae.
 */
@Injectable({ providedIn: 'root' })
export class EventService {
  private readonly events = new Subject<ServerEvent>();
  private readonly connectionState = new Subject<boolean>();
  private readonly source = new EventSource(`${environment.apiUrl}/events`);

  /** Solo eventos de transacción (created/updated/canceled). */
  readonly changes$: Observable<ServerEvent> = this.events.pipe(
    filter((e) => e.type.startsWith('transaction.')),
  );
  /** Solo eventos de precio en vivo. */
  readonly priceUpdates$: Observable<ServerEvent> = this.events.pipe(
    filter((e) => e.type === 'price'),
  );
  /** Solo eventos de señal de mercado (LONG/SHORT/NEUTRAL). */
  readonly analysis$: Observable<ServerEvent> = this.events.pipe(
    filter((e) => e.type === 'market.analysis'),
  );
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
    this.source.addEventListener('market.analysis', (e) => this.emit('market.analysis', e));
    this.source.addEventListener('price', (e) => this.emit('price', e));
  }

  private emit(type: string, event: MessageEvent): void {
    try {
      this.events.next({ type, data: JSON.parse(event.data) });
    } catch (err) {
      console.warn('[SSE] evento inválido', err);
    }
  }
}
