import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-asset-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="portfolio-item">
      <div class="asset-icon" [style.color]="iconColor" [style.border-color]="iconBorder">
        {{ label.substring(0, 2) }}
      </div>
      <div style="font-size: 0.7rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.25rem;">{{ label }}</div>
      <div style="font-size: 1.6rem; font-weight: 900; color: #fff; letter-spacing: -0.5px;">{{ amount }}</div>
      <div *ngIf="subLabel" style="margin-top: auto; padding-top: 1rem;">
        <div [style.color]="subLabelColor || 'var(--primary)'" 
             [style.background]="subLabelBg || 'rgba(0, 210, 255, 0.05)'"
             style="font-size: 0.6rem; font-weight: 800; padding: 0.2rem 0.5rem; border-radius: 4px; display: inline-block;">
          {{ subLabel }}
        </div>
      </div>
      <div *ngIf="locked > 0" style="margin-top: 0.5rem; font-size: 0.65rem; color: #6b7280;">
        Locked: {{ locked | number:'1.2-2' }}
      </div>
    </div>
  `
})
export class AssetCard {
  @Input() label: string = '';
  @Input() amount: any = '';
  @Input() locked: number = 0;
  @Input() iconColor: string = 'var(--text-main)';
  @Input() iconBorder: string = 'rgba(255,255,255,0.1)';
  @Input() subLabel?: string;
  @Input() subLabelColor?: string;
  @Input() subLabelBg?: string;
}
