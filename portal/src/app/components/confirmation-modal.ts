import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-confirmation-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content glass-card shadow-lg" (click)="$event.stopPropagation()">
        <header class="modal-header">
          <h3 class="gradient-text">¿Estás seguro?</h3>
          <button class="close-btn" (click)="close.emit()">&times;</button>
        </header>
        
        <div class="modal-body">
          <p style="color: #e5e7eb; font-size: 1.1rem; margin-bottom: 1rem;">{{ message }}</p>
          <div style="padding: 1rem; background: rgba(255,255,255,0.03); border-radius: 0.5rem; border: 1px solid rgba(255,255,255,0.05);">
            <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.25rem;">Detalles de la operación</div>
            <div style="font-size: 1rem; font-weight: 700; color: #fff; white-space: pre-line;">{{ details }}</div>
          </div>
        </div>

        <footer class="modal-footer" style="gap: 0.75rem;">
          <button class="btn-secondary" style="border-radius: 100px; padding: 0.5rem 1.25rem;" (click)="close.emit()">Cancelar</button>
          <button class="btn-primary" [style.background]="confirmColor" style="border:none; border-radius: 100px; padding: 0.5rem 1.25rem;" (click)="confirm.emit()">Confirmar</button>
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
      max-width: 450px;
      display: flex;
      flex-direction: column;
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    }
    .modal-header {
      padding: 1.25rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-header h3 { margin: 0; font-size: 1.3rem; }
    .close-btn {
      background: transparent; border: none; color: var(--text-muted);
      font-size: 1.5rem; cursor: pointer; transition: color 0.3s;
    }
    .close-btn:hover { color: #fff; }
    .modal-body {
      padding: 1.5rem;
    }
    .modal-footer {
      padding: 1.25rem; border-top: 1px solid rgba(255,255,255,0.05);
      display: flex; justify-content: flex-end;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  `]
})
export class ConfirmationModalComponent {
  @Input() message: string = '¿Deseas continuar con esta acción?';
  @Input() details: string = '';
  @Input() confirmColor: string = 'linear-gradient(135deg,#10b981,#059669)';
  @Output() close = new EventEmitter<void>();
  @Output() confirm = new EventEmitter<void>();
}
