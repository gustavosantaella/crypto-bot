import { Component, OnInit, OnDestroy, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { interval, Subscription } from 'rxjs';

declare var Chart: any;

@Component({
  selector: 'app-performance',
  standalone: true,
  imports: [CommonModule],
  template: `
<div class="page-wrapper">
  <header class="page-header">
    <div class="header-brand">
      <h1 class="gradient-text">Performance <span style="font-weight:300;opacity:.8">Analytics</span></h1>
      <p>Historial de rendimiento del bot — {{ activeSymbol }} Futures</p>
    </div>
    <div class="header-actions">
      <button (click)="go('/')" class="btn-secondary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;">← Dashboard</button>
      <button (click)="go('/signals')" class="btn-primary" style="border-radius:100px;padding:.5rem 1rem;font-size:.75rem;background:linear-gradient(135deg,var(--primary),#8b5cf6);border:none;">Signals</button>
      <div class="status-pill">
        <div [style.background-color]="health?.bot_alive ? 'var(--success)' : '#f59e0b'"
             style="width:10px;height:10px;border-radius:50%;flex-shrink:0;box-shadow:0 0 10px currentcolor;"></div>
        <span>{{ health?.bot_alive ? 'BOT ALIVE' : 'BOT IDLE' }}</span>
      </div>
    </div>
  </header>

  <!-- KPI Row -->
  <div class="metrics-bar" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr));">
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">TOTAL PnL</div>
      <div style="font-size:1.6rem;font-weight:900;" [style.color]="(stats?.total_pnl||0)>=0?'var(--success)':'var(--danger)'">
        {{ (stats?.total_pnl||0) >= 0 ? '+' : '' }}{{ (stats?.total_pnl||0) | number:'1.2-2' }}
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);">USDT</div>
    </div>
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">WIN RATE</div>
      <div style="font-size:1.6rem;font-weight:900;" [style.color]="(stats?.win_rate||0)>=50?'var(--success)':'var(--danger)'">
        {{ (stats?.win_rate||0) | number:'1.1-1' }}%
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);">{{ stats?.winning_trades||0 }}W / {{ stats?.losing_trades||0 }}L</div>
    </div>
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">BEST TRADE</div>
      <div style="font-size:1.6rem;font-weight:900;color:var(--success);">
        +{{ (stats?.best_trade||0) | number:'1.2-2' }}
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);">USDT</div>
    </div>
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">WORST TRADE</div>
      <div style="font-size:1.6rem;font-weight:900;color:var(--danger);">
        {{ (stats?.worst_trade||0) | number:'1.2-2' }}
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);">USDT</div>
    </div>
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">AVG HOLD</div>
      <div style="font-size:1.6rem;font-weight:900;color:var(--primary);">
        {{ (stats?.avg_hold_time_h||0) | number:'1.1-1' }}h
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);">Por operación</div>
    </div>
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">STREAK</div>
      <div style="font-size:1.6rem;font-weight:900;" [style.color]="(stats?.current_streak||0)>0?'var(--success)':'var(--danger)'">
        {{ (stats?.current_streak||0) > 0 ? '+' : '' }}{{ stats?.current_streak||0 }}
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);">{{ (stats?.current_streak||0) > 0 ? 'Ganadora' : 'Perdedora' }}</div>
    </div>
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">VOLUMEN</div>
      <div style="font-size:1.3rem;font-weight:900;color:#a78bfa;">
        {{ (stats?.total_volume||0) | number:'1.0-0' }}
      </div>
      <div style="font-size:.6rem;color:var(--text-muted);">USDT nocional</div>
    </div>
    <div class="glass-card" style="padding:1rem;text-align:center;">
      <div style="font-size:.6rem;color:var(--text-muted);font-weight:700;letter-spacing:1px;margin-bottom:.3rem;">UPTIME</div>
      <div style="font-size:1.3rem;font-weight:900;color:var(--primary);">{{ formatUptime(health?.uptime_seconds) }}</div>
      <div style="font-size:.6rem;color:var(--text-muted);">API activa</div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:2fr 1fr;gap:1.5rem;margin-top:0;">

    <!-- PnL Chart -->
    <div class="glass-card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:.5rem;">
        <h3 style="color:var(--text-muted);margin:0;font-size:1rem;">PnL Acumulado por Dia</h3>
        <div style="display:flex;gap:.4rem;">
          <button *ngFor="let d of [7,14,30,90]" (click)="loadPnL(d)"
            [style.background]="selectedDays===d?'var(--primary)':'rgba(255,255,255,.05)'"
            [style.color]="selectedDays===d?'#000':'var(--text-muted)'"
            style="border:1px solid var(--border);padding:.2rem .6rem;border-radius:6px;font-size:.65rem;font-weight:700;cursor:pointer;">
            {{ d }}D
          </button>
        </div>
      </div>
      <div style="height:280px;position:relative;"><canvas id="pnlChart"></canvas></div>
    </div>

    <!-- Win/Loss Donut -->
    <div class="glass-card" style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
      <h3 style="color:var(--text-muted);margin:0 0 1rem;font-size:1rem;">Win / Loss Ratio</h3>
      <div style="height:200px;width:200px;position:relative;"><canvas id="donutChart"></canvas></div>
      <div style="margin-top:1rem;display:flex;gap:1.5rem;font-size:.7rem;">
        <div style="display:flex;align-items:center;gap:.4rem;">
          <div style="width:10px;height:10px;border-radius:50%;background:var(--success);"></div>
          <span style="color:var(--text-muted);">Wins: <b style="color:var(--success);">{{ stats?.winning_trades||0 }}</b></span>
        </div>
        <div style="display:flex;align-items:center;gap:.4rem;">
          <div style="width:10px;height:10px;border-radius:50%;background:var(--danger);"></div>
          <span style="color:var(--text-muted);">Losses: <b style="color:var(--danger);">{{ stats?.losing_trades||0 }}</b></span>
        </div>
      </div>
    </div>

  </div>

  <!-- RSI Distribution at Entry -->
  <div class="glass-card" style="margin-top:1.5rem;">
    <h3 style="color:var(--text-muted);margin:0 0 1.5rem;font-size:1rem;">RSI en Entradas BUY — Calidad de Senales</h3>
    <div style="height:200px;position:relative;"><canvas id="rsiChart"></canvas></div>
    <p style="font-size:.65rem;color:var(--text-muted);margin-top:.75rem;text-align:center;">
      Un bot conservador deberia tener la mayoria de entradas en RSI 25–40. Barras a la izquierda = mayor calidad de entrada.
    </p>
  </div>
</div>
  `
})
export class PerformanceComponent implements OnInit, OnDestroy, AfterViewInit {
  stats: any = null;
  health: any = null;
  selectedDays = 30;
  pnlData: any[] = [];
  rsiData: any[] = [];
  botStatus: any = null;

  get activeSymbol(): string {
    return this.botStatus?.symbol || 'CRYPTO';
  }

  private pnlChart: any;
  private donutChart: any;
  private rsiChart: any;
  private sub?: Subscription;

  constructor(private api: ApiService, private router: Router, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.fetchAll();
    this.sub = interval(60000).subscribe(() => this.fetchAll());
  }

  ngAfterViewInit() {
    // Charts se inicializan cuando los datos llegan
  }

  ngOnDestroy() { this.sub?.unsubscribe(); }

  go(path: string) { this.router.navigate([path]); }

  fetchAll() {
    this.api.getStatsSummary().subscribe({ next: d => { this.stats = d; this.cdr.detectChanges(); this.buildDonut(); } });
    this.api.getHealth().subscribe({ next: d => { this.health = d; this.cdr.detectChanges(); } });
    this.api.getBotStatus().subscribe({ next: d => { this.botStatus = d; this.cdr.detectChanges(); } });
    this.loadPnL(this.selectedDays);
    this.api.getRsiDistribution().subscribe({ next: d => { this.rsiData = d.buckets || []; this.buildRsiChart(); } });
  }

  loadPnL(days: number) {
    this.selectedDays = days;
    this.api.getPnLOverTime(days).subscribe({ next: d => { this.pnlData = d.series || []; this.buildPnLChart(); } });
  }

  buildPnLChart() {
    const ctx = document.getElementById('pnlChart') as HTMLCanvasElement;
    if (!ctx) return;
    if (this.pnlChart) this.pnlChart.destroy();

    const cumulative: number[] = [];
    let acc = 0;
    const colors = this.pnlData.map(d => { acc += d.pnl; return d.pnl >= 0 ? 'rgba(16,185,129,0.8)' : 'rgba(239,68,68,0.8)'; });
    const cumulativeColors: string[] = [];
    let acc2 = 0;
    this.pnlData.forEach(d => { acc2 += d.pnl; cumulative.push(acc2); cumulativeColors.push(acc2 >= 0 ? '#10b981' : '#ef4444'); });

    this.pnlChart = new Chart(ctx, {
      data: {
        labels: this.pnlData.map(d => d.date),
        datasets: [
          {
            type: 'bar',
            label: 'PnL diario',
            data: this.pnlData.map(d => d.pnl),
            backgroundColor: colors,
            yAxisID: 'y'
          },
          {
            type: 'line',
            label: 'PnL acumulado',
            data: cumulative,
            borderColor: '#00d2ff',
            backgroundColor: 'rgba(0,210,255,0.05)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.4,
            yAxisID: 'y'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: '#9ca3af', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
          y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } }
        },
        plugins: { legend: { labels: { color: '#9ca3af', font: { size: 10 } } } }
      }
    });
  }

  buildDonut() {
    const ctx = document.getElementById('donutChart') as HTMLCanvasElement;
    if (!ctx || !this.stats) return;
    if (this.donutChart) this.donutChart.destroy();

    const wins   = this.stats.winning_trades || 0;
    const losses = this.stats.losing_trades  || 0;

    this.donutChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Wins', 'Losses'],
        datasets: [{
          data: [wins, losses],
          backgroundColor: ['rgba(16,185,129,0.8)', 'rgba(239,68,68,0.8)'],
          borderColor:      ['#10b981', '#ef4444'],
          borderWidth: 2,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx: any) => ` ${ctx.label}: ${ctx.raw}` } }
        },
        cutout: '70%'
      }
    });
  }

  buildRsiChart() {
    const ctx = document.getElementById('rsiChart') as HTMLCanvasElement;
    if (!ctx) return;
    if (this.rsiChart) this.rsiChart.destroy();

    // Color degradado: zonas bajas de RSI = verde (buena señal), altas = rojo
    const bgColors = this.rsiData.map((b: any) => {
      const idx = this.rsiData.indexOf(b);
      if (idx < 3) return 'rgba(16,185,129,0.8)';
      if (idx < 5) return 'rgba(251,191,36,0.7)';
      return 'rgba(239,68,68,0.6)';
    });

    this.rsiChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.rsiData.map((b: any) => b.range),
        datasets: [{
          label: 'Entradas BUY',
          data: this.rsiData.map((b: any) => b.count),
          backgroundColor: bgColors,
          borderRadius: 6,
          borderSkipped: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
          y: { ticks: { color: '#9ca3af', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  formatUptime(s: number): string {
    if (!s) return '---';
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }
}
