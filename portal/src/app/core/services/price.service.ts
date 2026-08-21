import { Injectable, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EventService } from './event.service';

export interface PriceInfo {
  symbol: string;
  price: number;
  time: number;
}

/**
 * Precio en vivo de Binance recibido por SSE.
 *
 * La API publica el precio de cada ambiente (testnet y producción); aquí se
 * guarda el último de cada uno para consultarlo según el switch del sidebar.
 */
@Injectable({ providedIn: 'root' })
export class PriceService {
  private readonly prices = signal<Record<string, PriceInfo>>({});
  private readonly eventService = inject(EventService);

  constructor() {
    this.eventService.priceUpdates$
      .pipe(takeUntilDestroyed())
      .subscribe((e) => {
        const data = e.data as { test_mode: boolean; symbol: string; price: number; time: number };
        this.prices.update((m) => ({
          ...m,
          [String(data.test_mode)]: {
            symbol: data.symbol,
            price: data.price,
            time: data.time,
          },
        }));
      });
  }

  /** Último precio del ambiente indicado (true=testnet, false=producción). */
  priceFor(testMode: boolean): PriceInfo | undefined {
    return this.prices()[String(testMode)];
  }
}
