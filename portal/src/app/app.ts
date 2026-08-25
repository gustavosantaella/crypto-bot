import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { EnvironmentService } from './core/services/environment.service';
import { PriceService } from './core/services/price.service';
import { NumPipe } from './shared/pipes/num.pipe';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NumPipe],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly environmentService = inject(EnvironmentService);
  private readonly priceService = inject(PriceService);

  /** true = Testnet | false = Producción. */
  readonly testMode = this.environmentService.testMode$;

  /** 'SPOT' | 'FUTURES'. */
  readonly marketType = this.environmentService.marketType$;

  /** Precio en vivo del ambiente seleccionado (vía SSE). */
  readonly price = computed(() => this.priceService.priceFor(this.testMode()));

  toggleAmbient(): void {
    this.environmentService.toggle();
  }

  toggleMarketType(): void {
    this.environmentService.toggleMarketType();
  }
}


