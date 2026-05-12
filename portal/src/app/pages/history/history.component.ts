import { Component, OnInit, OnDestroy, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../api.service';
import { WebsocketService } from '../../websocket.service';
import { Subscription } from 'rxjs';

declare var Chart: any;

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './history.component.html'
})
export class HistoryComponent implements OnInit, OnDestroy, AfterViewInit {
  allPriceLogs: any[] = [];
  currentPage: number = 1;
  pageSize: number = 15;
  totalLogs: number = 0;
  startDate: string = '';
  endDate: string = '';
  
  private chart: any;
  private wsSub?: Subscription;

  constructor(
    private apiService: ApiService,
    private wsService: WebsocketService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadInitialData();
    
    this.wsSub = this.wsService.getMessages().subscribe(msg => {
      if (msg.type === 'PRICE_UPDATE') {
        const data = msg.data;
        const newLog = {
          symbol: data.symbol,
          price: parseFloat(data.price || '0'),
          rsi: parseFloat(data.rsi || '0'),
          timestamp: data.timestamp || new Date().toISOString()
        };
        this.allPriceLogs.unshift(newLog);
        if (this.allPriceLogs.length > 200) this.allPriceLogs.pop();
        this.totalLogs = this.allPriceLogs.length;
        this.updateChart();
        this.cdr.detectChanges();
      }
    });
  }

  ngAfterViewInit() {
    this.initChart();
  }

  loadInitialData() {
    this.apiService.getPriceLogs(0, 100).subscribe(logs => {
      this.allPriceLogs = logs.map(l => ({
        ...l,
        price: parseFloat(l.price),
        rsi: parseFloat(l.rsi)
      }));
      this.totalLogs = this.allPriceLogs.length;
      this.updateChart();
      this.cdr.detectChanges();
    });
  }

  initChart() {
    const ctx = document.getElementById('rsiChart') as HTMLCanvasElement;
    if (!ctx) return;

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Price (USDT)',
            data: [],
            borderColor: '#00d2ff',
            backgroundColor: 'rgba(0, 210, 255, 0.1)',
            yAxisID: 'yPrice',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.4
          },
          {
            label: 'RSI Indicator',
            data: [],
            borderColor: '#fbbf24',
            backgroundColor: 'transparent',
            yAxisID: 'yRsi',
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            display: false
          },
          yPrice: {
            type: 'linear',
            display: true,
            position: 'left',
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#9ca3af' }
          },
          yRsi: {
            type: 'linear',
            display: true,
            position: 'right',
            min: 0,
            max: 100,
            grid: { drawOnChartArea: false },
            ticks: { color: '#fbbf24' }
          }
        },
        plugins: {
          legend: {
            labels: { color: '#f3f4f6' }
          }
        }
      }
    });
  }

  updateChart() {
    if (!this.chart || this.allPriceLogs.length === 0) return;

    const displayLogs = [...this.allPriceLogs].reverse();
    this.chart.data.labels = displayLogs.map(l => this.formatDate(l.timestamp));
    this.chart.data.datasets[0].data = displayLogs.map(l => l.price);
    this.chart.data.datasets[1].data = displayLogs.map(l => l.rsi);
    this.chart.update('none'); // Update without animation for performance
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
  }

  loadPage(page: number) {
    this.currentPage = page;
  }

  get totalPages() {
    return Math.ceil(this.totalLogs / this.pageSize);
  }

  goBack() {
    this.router.navigate(['/']);
  }

  formatPrice(price: any) { return parseFloat(price).toFixed(4); }
  formatDate(dateStr: string) {
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? '---' : date.toLocaleTimeString();
  }
}
