import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="glass-card" [style.border-left]="'4px solid ' + color" style="padding: 1.25rem;">
      <h4 style="color: var(--text-muted); margin: 0; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">{{ title }}</h4>
      <p [style.color]="valueColor || 'var(--text-main)'" style="font-size: 1.75rem; font-weight: 700; margin: 0.4rem 0;">
        {{ prefix }}{{ value }} <span *ngIf="suffix" style="font-size: 0.9rem; opacity: 0.6;">{{ suffix }}</span>
      </p>
    </div>
  `
})
export class MetricCard {
  @Input() title: string = '';
  @Input() value: any = '';
  @Input() color: string = 'var(--primary)';
  @Input() valueColor?: string;
  @Input() prefix: string = '';
  @Input() suffix: string = '';
}
