import { Injectable, signal } from '@angular/core';

/**
 * Ambiente que el usuario selecciona en el switch del sidebar.
 *
 * Solo afecta a la VISUALIZACIÓN de datos (balance, transacciones, stats);
 * no tiene relación con el bot. Se persiste en localStorage.
 */
@Injectable({ providedIn: 'root' })
export class EnvironmentService {
  private readonly _testMode = signal(true);

  /** true = Testnet | false = Producción. */
  readonly testMode$ = this._testMode.asReadonly();

  constructor() {
    const saved = localStorage.getItem('crypto-bot.ambient');
    if (saved === 'prod') this._testMode.set(false);
    else if (saved === 'test') this._testMode.set(true);
  }

  get testMode(): boolean {
    return this._testMode();
  }

  setTestMode(testMode: boolean): void {
    this._testMode.set(testMode);
    localStorage.setItem('crypto-bot.ambient', testMode ? 'test' : 'prod');
  }

  toggle(): void {
    this.setTestMode(!this._testMode());
  }
}
