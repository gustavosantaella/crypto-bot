import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { EnvironmentService } from './core/services/environment.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly environmentService = inject(EnvironmentService);

  /** true = Testnet | false = Producción. */
  readonly testMode = this.environmentService.testMode$;

  toggleAmbient(): void {
    this.environmentService.toggle();
  }
}

