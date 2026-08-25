import { Injectable, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { MarketAnalysis } from '../models/market-analysis.model';
import { MarketType } from '../models/transaction.model';
import { EventService } from './event.service';

/**
 * Señal de mercado en vivo (LONG/SHORT/NEUTRAL).
 *
 * La API publica eventos ``market.analysis`` por SSE para cada combinación de
 * ambiente (testnet/producción) y mercado (spot/futuros); este servicio
 * guarda el último valor de cada una para consultarlo según el switch del
 * sidebar.
 */
@Injectable({ providedIn: 'root' })
export class MarketSignalService {
  private readonly signals = signal<Record<string, MarketAnalysis>>({});
  private readonly eventService = inject(EventService);

  constructor() {
    this.eventService.analysis$
      .pipe(takeUntilDestroyed())
      .subscribe((e) => {
        const data = e.data as MarketAnalysis;
        if (!data || typeof data !== 'object') return;
        const key = `${data.market_type}:${data.test_mode}`;
        this.signals.update((m) => ({ ...m, [key]: data }));
      });
  }

  /** Última señal del ambiente y mercado indicados. */
  signalFor(testMode: boolean, marketType: MarketType): MarketAnalysis | undefined {
    return this.signals()[`${marketType}:${testMode}`];
  }
}
