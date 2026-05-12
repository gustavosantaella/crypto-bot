import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-ai-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content glass-card shadow-lg" (click)="$event.stopPropagation()">
        <header class="modal-header">
          <h3 class="gradient-text">
            <span class="ai-sparkle">✨</span> DeepSeek Market Analysis
          </h3>
          <button class="close-btn" (click)="close.emit()">&times;</button>
        </header>
        
        <div class="modal-body custom-scroll">
          <div *ngIf="loading" class="loading-state">
            <div class="spinner"></div>
            <p>Consultando a la IA experta...</p>
          </div>
          
          <div *ngIf="!loading && analysis" class="analysis-container">
            <div class="analysis-text" [innerHTML]="formatResponse(analysis)"></div>
          </div>

          <div *ngIf="!loading && error" class="error-state">
            <p>{{ error }}</p>
          </div>
        </div>

        <footer class="modal-footer">
          <button class="btn-primary" (click)="close.emit()">ENTENDIDO</button>
        </footer>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0, 0, 0, 0.85);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      animation: fadeIn 0.3s ease;
    }
    .modal-content {
      width: 90%;
      max-width: 650px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      border: 1px solid rgba(0, 210, 255, 0.3);
      box-shadow: 0 0 50px rgba(0, 210, 255, 0.15);
    }
    .modal-header {
      padding: 1.5rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-header h3 { margin: 0; font-size: 1.5rem; }
    .close-btn {
      background: transparent; border: none; color: var(--text-muted);
      font-size: 2rem; cursor: pointer; transition: color 0.3s;
    }
    .close-btn:hover { color: #fff; }
    .modal-body {
      padding: 1.5rem;
      overflow-y: auto;
      flex: 1;
    }
    .loading-state {
      text-align: center; padding: 3rem 0;
      color: var(--primary); font-weight: 700;
    }
    .spinner {
      width: 40px; height: 40px;
      border: 3px solid rgba(0, 210, 255, 0.1);
      border-top-color: var(--primary);
      border-radius: 50%;
      margin: 0 auto 1rem;
      animation: spin 1s linear infinite;
    }
    .analysis-text {
      color: #e5e7eb; line-height: 1.8; font-size: 1rem;
    }
    .modal-footer {
      padding: 1.25rem; border-top: 1px solid var(--border);
      display: flex; justify-content: flex-end;
    }
    .custom-scroll::-webkit-scrollbar { width: 6px; }
    .custom-scroll::-webkit-scrollbar-track { background: transparent; }
    .custom-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  `]
})
export class AiModalComponent {
  @Input() loading: boolean = false;
  @Input() analysis: string = '';
  @Input() error: string = '';
  @Output() close = new EventEmitter<void>();

  formatResponse(text: string): string {
    if (!text) return '';
    // Formatear negritas y saltos de línea para que se vea profesional
    return text
      .replace(/\*\*(.*?)\*\*/g, '<b style="color: var(--primary); font-size: 1.1rem;">$1</b>')
      .replace(/\n/g, '<br>');
  }
}
