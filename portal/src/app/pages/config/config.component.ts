import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';

interface ConfigItem {
  id: number;
  key: string;
  value: string;
  env_default: string;
  enabled: boolean;
  category: string;
  label: string;
  description: string;
  dtype: string;
  // UI state
  editing?: boolean;
  editValue?: string;
  saving?: boolean;
  dirty?: boolean;
}

@Component({
  selector: 'app-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
<div class="page-wrapper">
  <header class="page-header">
    <div class="header-brand">
      <h1 class="gradient-text">Bot <span style="font-weight:300;opacity:.8">Config</span></h1>
      <p>Parámetros en tiempo real — los valores activos sobreescriben el .env</p>
    </div>
    <div class="header-actions">
      <button (click)="go('/')" class="btn-secondary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;">Dashboard</button>
      <button (click)="go('/signals')" class="btn-primary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;background:linear-gradient(135deg,#f59e0b,#ef4444);border:none;">Signals</button>
      <button (click)="resetAll()" class="btn-secondary"
              style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;border-color:rgba(239,68,68,.4);color:var(--danger);"
              [disabled]="resetting">
        {{ resetting ? 'Reseteando...' : '↺ Reset a .env' }}
      </button>
    </div>
  </header>

  <!-- Legend -->
  <div class="glass-card" style="padding:.75rem 1.25rem;margin-bottom:1rem;display:flex;align-items:center;gap:2rem;flex-wrap:wrap;">
    <div style="display:flex;align-items:center;gap:.5rem;font-size:.72rem;color:var(--text-muted);">
      <div style="width:10px;height:10px;border-radius:50%;background:var(--success);box-shadow:0 0 6px var(--success);"></div>
      Switch ON → el bot usa el valor de esta tabla
    </div>
    <div style="display:flex;align-items:center;gap:.5rem;font-size:.72rem;color:var(--text-muted);">
      <div style="width:10px;height:10px;border-radius:50%;background:rgba(255,255,255,.2);"></div>
      Switch OFF → el bot usa el valor del .env
    </div>
    <div style="font-size:.72rem;color:var(--text-muted);margin-left:auto;">
      <b style="color:var(--primary);">{{ activeCount }}</b> de <b>{{ items.length }}</b> parámetros activos
    </div>
  </div>

  <!-- Loading -->
  <div *ngIf="loading" style="text-align:center;padding:3rem;color:var(--text-muted);">
    Cargando configuración...
  </div>

  <!-- Categories -->
  <ng-container *ngFor="let cat of categories">
    <div class="glass-card" style="margin-bottom:1.25rem;padding:0;overflow:hidden;">
      <!-- Category Header -->
      <div [style.background]="catColor(cat)"
           style="padding:.75rem 1.25rem;display:flex;align-items:center;gap:.75rem;border-bottom:1px solid rgba(255,255,255,.06);">
        <span style="font-size:1.1rem;">{{ catIcon(cat) }}</span>
        <span style="font-size:.85rem;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;color:#fff;">{{ cat }}</span>
        <span style="font-size:.65rem;color:rgba(255,255,255,.5);margin-left:auto;">
          {{ itemsByCategory(cat).length }} parámetros
        </span>
      </div>

      <!-- Params Table -->
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="border-bottom:1px solid rgba(255,255,255,.04);">
              <th style="padding:.5rem 1rem;font-size:.6rem;color:var(--text-muted);text-align:left;font-weight:700;text-transform:uppercase;letter-spacing:1px;width:36px;">ON</th>
              <th style="padding:.5rem 1rem;font-size:.6rem;color:var(--text-muted);text-align:left;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Parámetro</th>
              <th style="padding:.5rem 1rem;font-size:.6rem;color:var(--text-muted);text-align:left;font-weight:700;text-transform:uppercase;letter-spacing:1px;width:160px;">Valor Activo</th>
              <th style="padding:.5rem 1rem;font-size:.6rem;color:var(--text-muted);text-align:left;font-weight:700;text-transform:uppercase;letter-spacing:1px;width:120px;">Default (.env)</th>
              <th style="padding:.5rem 1rem;font-size:.6rem;color:var(--text-muted);text-align:left;font-weight:700;text-transform:uppercase;letter-spacing:1px;width:80px;">Tipo</th>
              <th style="padding:.5rem 1rem;font-size:.6rem;color:var(--text-muted);text-align:left;font-weight:700;text-transform:uppercase;letter-spacing:1px;width:80px;"></th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let item of itemsByCategory(cat)"
                [style.opacity]="item.enabled ? '1' : '.55'"
                style="border-bottom:1px solid rgba(255,255,255,.03);transition:opacity .2s;">

              <!-- Switch -->
              <td style="padding:.6rem 1rem;">
                <div class="toggle-wrap" (click)="toggleEnabled(item)">
                  <div class="toggle-track" [class.on]="item.enabled">
                    <div class="toggle-thumb"></div>
                  </div>
                </div>
              </td>

              <!-- Label + Key + Description -->
              <td style="padding:.6rem 1rem;">
                <div style="font-size:.78rem;font-weight:700;color:#fff;">{{ item.label }}</div>
                <div style="font-size:.6rem;font-family:monospace;color:var(--primary);margin:.1rem 0;">{{ item.key }}</div>
                <div style="font-size:.6rem;color:var(--text-muted);line-height:1.3;">{{ item.description }}</div>
              </td>

              <!-- Value Editor -->
              <td style="padding:.6rem 1rem;">
                <div *ngIf="!item.editing" style="display:flex;align-items:center;gap:.5rem;">
                  <span style="font-size:.85rem;font-weight:800;"
                        [style.color]="item.enabled ? 'var(--success)' : 'var(--text-muted)'">
                    {{ displayValue(item) }}
                  </span>
                  <button *ngIf="item.enabled" (click)="startEdit(item)"
                          style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);color:var(--text-muted);border-radius:4px;padding:.1rem .4rem;font-size:.6rem;cursor:pointer;">
                    ✏️
                  </button>
                </div>
                <div *ngIf="item.editing" style="display:flex;align-items:center;gap:.4rem;">
                  <input *ngIf="item.dtype !== 'bool'" type="text" [(ngModel)]="item.editValue"
                         (keydown.enter)="saveEdit(item)" (keydown.escape)="cancelEdit(item)"
                         style="background:rgba(0,210,255,.08);border:1px solid rgba(0,210,255,.3);color:#fff;border-radius:6px;padding:.3rem .5rem;font-size:.78rem;font-family:monospace;width:100px;outline:none;">
                  <select *ngIf="item.dtype === 'bool'" [(ngModel)]="item.editValue"
                          style="background:rgba(0,210,255,.08);border:1px solid rgba(0,210,255,.3);color:#fff;border-radius:6px;padding:.3rem .5rem;font-size:.78rem;outline:none;">
                    <option value="True">True</option>
                    <option value="False">False</option>
                  </select>
                  <button (click)="saveEdit(item)" [disabled]="item.saving"
                          style="background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.3);color:var(--success);border-radius:4px;padding:.2rem .5rem;font-size:.65rem;cursor:pointer;">
                    {{ item.saving ? '...' : '✔' }}
                  </button>
                  <button (click)="cancelEdit(item)"
                          style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:var(--danger);border-radius:4px;padding:.2rem .5rem;font-size:.65rem;cursor:pointer;">
                    ✕
                  </button>
                </div>
              </td>

              <!-- Default -->
              <td style="padding:.6rem 1rem;">
                <span style="font-size:.75rem;color:var(--text-muted);font-family:monospace;">
                  {{ item.env_default }}
                </span>
                <button *ngIf="item.value !== item.env_default && item.enabled"
                        (click)="resetItem(item)"
                        style="display:block;margin-top:.2rem;background:none;border:none;color:rgba(245,158,11,.7);font-size:.6rem;cursor:pointer;padding:0;">
                  ↺ restaurar
                </button>
              </td>

              <!-- Type badge -->
              <td style="padding:.6rem 1rem;">
                <span style="font-size:.6rem;font-weight:700;padding:.15rem .45rem;border-radius:4px;"
                      [style.background]="dtypeColor(item.dtype) + '22'"
                      [style.color]="dtypeColor(item.dtype)">
                  {{ item.dtype }}
                </span>
              </td>

              <!-- Modified indicator -->
              <td style="padding:.6rem 1rem;text-align:center;">
                <span *ngIf="item.value !== item.env_default"
                      style="font-size:.6rem;color:#f59e0b;font-weight:700;">MODIFIED</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </ng-container>

  <!-- Toast -->
  <div *ngIf="toast" class="toast-msg" [class.show]="toast">{{ toast }}</div>
</div>
  `,
  styles: [`
    .toggle-wrap { cursor: pointer; display: inline-flex; }
    .toggle-track {
      width: 36px; height: 20px; border-radius: 100px;
      background: rgba(255,255,255,.12); position: relative;
      transition: background .2s; border: 1px solid rgba(255,255,255,.1);
    }
    .toggle-track.on { background: rgba(16,185,129,.4); border-color: var(--success); }
    .toggle-thumb {
      position: absolute; top: 2px; left: 2px;
      width: 14px; height: 14px; border-radius: 50%;
      background: rgba(255,255,255,.5); transition: left .2s, background .2s;
    }
    .toggle-track.on .toggle-thumb { left: 18px; background: var(--success); }
    .toast-msg {
      position: fixed; bottom: 2rem; right: 2rem;
      background: rgba(16,185,129,.15); border: 1px solid rgba(16,185,129,.3);
      color: var(--success); padding: .75rem 1.5rem; border-radius: 8px;
      font-size: .8rem; font-weight: 700; opacity: 0; transition: opacity .3s;
      z-index: 9999;
    }
    .toast-msg.show { opacity: 1; }
  `]
})
export class ConfigComponent implements OnInit {
  items: ConfigItem[] = [];
  loading = true;
  resetting = false;
  toast = '';
  private _toastTimer: any;

  get categories(): string[] {
    const seen = new Set<string>();
    return this.items
      .map(i => i.category)
      .filter(c => { if (seen.has(c)) return false; seen.add(c); return true; });
  }

  get activeCount(): number {
    return this.items.filter(i => i.enabled).length;
  }

  constructor(private api: ApiService, private router: Router, private cdr: ChangeDetectorRef) {}

  ngOnInit() { this.load(); }

  go(path: string) { this.router.navigate([path]); }

  load() {
    this.loading = true;
    this.api.getConfig().subscribe({
      next: (res: ConfigItem[]) => {
        this.items = res.map(i => ({ ...i, editing: false, editValue: i.value }));
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.showToast('Error al cargar configuración'); }
    });
  }

  itemsByCategory(cat: string): ConfigItem[] {
    return this.items.filter(i => i.category === cat);
  }

  toggleEnabled(item: ConfigItem) {
    const prev = item.enabled;
    item.enabled = !item.enabled;
    this.api.updateConfig(item.key, { enabled: item.enabled }).subscribe({
      next: () => this.showToast(`${item.label}: ${item.enabled ? 'ON ✅' : 'OFF ⛔'}`),
      error: () => { item.enabled = prev; this.showToast('Error al actualizar'); }
    });
  }

  startEdit(item: ConfigItem) {
    item.editValue = item.value;
    item.editing = true;
  }

  cancelEdit(item: ConfigItem) {
    item.editing = false;
  }

  saveEdit(item: ConfigItem) {
    if (item.editValue === undefined || item.editValue === item.value) {
      item.editing = false;
      return;
    }
    item.saving = true;
    const newVal = item.editValue!.trim();
    this.api.updateConfig(item.key, { value: newVal }).subscribe({
      next: (res: ConfigItem) => {
        item.value = res.value;
        item.editValue = res.value;
        item.editing = false;
        item.saving = false;
        this.showToast(`${item.label} → ${newVal}`);
        this.cdr.detectChanges();
      },
      error: () => {
        item.saving = false;
        this.showToast('Error al guardar');
      }
    });
  }

  resetItem(item: ConfigItem) {
    this.api.updateConfig(item.key, { value: item.env_default }).subscribe({
      next: (res: ConfigItem) => {
        item.value = res.value;
        item.editValue = res.value;
        this.showToast(`${item.label} restaurado a ${item.env_default}`);
        this.cdr.detectChanges();
      }
    });
  }

  resetAll() {
    if (!confirm('¿Restaurar TODOS los parámetros al valor del .env?')) return;
    this.resetting = true;
    this.api.resetConfig().subscribe({
      next: (res: ConfigItem[]) => {
        this.items = res.map(i => ({ ...i, editing: false, editValue: i.value }));
        this.resetting = false;
        this.showToast('Todos los parámetros restaurados ✅');
        this.cdr.detectChanges();
      },
      error: () => { this.resetting = false; this.showToast('Error al resetear'); }
    });
  }

  displayValue(item: ConfigItem): string {
    if (item.dtype === 'bool') return item.value === 'True' ? '✅ True' : '❌ False';
    if (item.dtype === 'float') return parseFloat(item.value).toString();
    return item.value;
  }

  catIcon(cat: string): string {
    const icons: Record<string,string> = {
      'General': '⚙️', 'Futuros': '⚡', 'RSI': '📈', 'ATR': '📊',
      'ADX': '🎯', 'EMA': '〰️', 'Trailing Stop': '🛡️', 'DCA': '🔁', 'Riesgo': '🚨'
    };
    return icons[cat] || '🔧';
  }

  catColor(cat: string): string {
    const colors: Record<string,string> = {
      'General':      'linear-gradient(135deg,rgba(0,210,255,.12),rgba(58,123,213,.08))',
      'Futuros':      'linear-gradient(135deg,rgba(245,158,11,.12),rgba(239,68,68,.08))',
      'RSI':          'linear-gradient(135deg,rgba(251,191,36,.12),rgba(245,158,11,.08))',
      'ATR':          'linear-gradient(135deg,rgba(139,92,246,.12),rgba(109,40,217,.08))',
      'ADX':          'linear-gradient(135deg,rgba(6,182,212,.12),rgba(14,116,144,.08))',
      'EMA':          'linear-gradient(135deg,rgba(16,185,129,.12),rgba(5,150,105,.08))',
      'Trailing Stop':'linear-gradient(135deg,rgba(52,211,153,.12),rgba(16,185,129,.08))',
      'DCA':          'linear-gradient(135deg,rgba(167,139,250,.12),rgba(139,92,246,.08))',
      'Riesgo':       'linear-gradient(135deg,rgba(239,68,68,.12),rgba(185,28,28,.08))',
    };
    return colors[cat] || 'rgba(255,255,255,.03)';
  }

  dtypeColor(dtype: string): string {
    const c: Record<string,string> = {
      'int': '#60a5fa', 'float': '#fbbf24', 'str': '#a78bfa', 'bool': '#34d399'
    };
    return c[dtype] || '#9ca3af';
  }

  showToast(msg: string) {
    this.toast = msg;
    this.cdr.detectChanges();
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => { this.toast = ''; this.cdr.detectChanges(); }, 2800);
  }
}
