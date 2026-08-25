import { Injectable, signal } from '@angular/core';

/** Mercados soportados por el sistema (spot y futuros USDT-M). */
export type MarketType = 'SPOT' | 'FUTURES';

/**
 * Preferencias de visualización del usuario (ambiente y mercado).
 *
 * Solo afectan a la VISUALIZACIÓN de datos (balance, transacciones, stats,
 * señal de mercado); no tienen relación directa con el bot. Se persisten en
 * localStorage.
 */
@Injectable({ providedIn: 'root' })
export class EnvironmentService {
  private readonly _testMode = signal(true);
  private readonly _marketType = signal<MarketType>('SPOT');

  /** true = Testnet | false = Producción. */
  readonly testMode$ = this._testMode.asReadonly();
  /** 'SPOT' | 'FUTURES'. */
  readonly marketType$ = this._marketType.asReadonly();

  constructor() {
    const saved = localStorage.getItem('crypto-bot.ambient');
    if (saved === 'prod') this._testMode.set(false);
    else if (saved === 'test') this._testMode.set(true);

    const savedMarket = localStorage.getItem('crypto-bot.market');
    if (savedMarket === 'FUTURES' || savedMarket === 'SPOT') {
      this._marketType.set(savedMarket);
    }
  }

  get testMode(): boolean {
    return this._testMode();
  }

  get marketType(): MarketType {
    return this._marketType();
  }

  setTestMode(testMode: boolean): void {
    this._testMode.set(testMode);
    localStorage.setItem('crypto-bot.ambient', testMode ? 'test' : 'prod');
  }

  setMarketType(marketType: MarketType): void {
    this._marketType.set(marketType);
    localStorage.setItem('crypto-bot.market', marketType);
  }

  toggle(): void {
    this.setTestMode(!this._testMode());
  }

  toggleMarketType(): void {
    this.setMarketType(this._marketType() === 'SPOT' ? 'FUTURES' : 'SPOT');
  }
}

