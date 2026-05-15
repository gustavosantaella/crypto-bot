import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-confirmation-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
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
            <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;">Detalles de la operación</div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 0.5rem;">
              <div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Símbolo</div>
                <div style="font-size: 1rem; font-weight: 700; color: #fff;">{{ symbol }}</div>
              </div>
              <div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Lado</div>
                <div style="font-size: 1rem; font-weight: 700;" [style.color]="side === 'BUY' ? 'var(--success)' : 'var(--danger)'">{{ side === 'BUY' ? 'LONG' : 'SHORT' }}</div>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
              <div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Precio Actual</div>
                <div style="font-size: 1.2rem; font-weight: 900; color: #fff;">$ {{ livePrice | number:'1.2-2' }}</div>
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Cantidad</label>
                <input type="number" [(ngModel)]="editableQuantity" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 0.5rem; border-radius: 0.25rem; font-size: 1rem;" />
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
              <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Stop Loss (SL)</label>
                <input type="number" [(ngModel)]="editableSl" (focus)="onEdit()" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 0.5rem; border-radius: 0.25rem; font-size: 1rem;" />
                <span *ngIf="!userEdited" style="font-size: 0.6rem; color: var(--primary);">Auto-calculado</span>
                <span *ngIf="userEdited" style="font-size: 0.6rem; color: #fbbf24;">Modificado</span>
              </div>
              <div>
                <label style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Take Profit (TP)</label>
                <input type="number" [(ngModel)]="editableTp" (focus)="onEdit()" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: #fff; padding: 0.5rem; border-radius: 0.25rem; font-size: 1rem;" />
                <span *ngIf="!userEdited" style="font-size: 0.6rem; color: var(--primary);">Auto-calculado</span>
                <span *ngIf="userEdited" style="font-size: 0.6rem; color: #fbbf24;">Modificado</span>
              </div>
            </div>

            <!-- Proyeccion de Ganancia/Perdida -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05);">
              <div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Ganancia Estimada</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: var(--success);">$ {{ calculateProfit() | number:'1.2-3' }}</div>
              </div>
              <div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Pérdida Máxima</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: var(--danger);">$ {{ calculateLoss() | number:'1.2-3' }}</div>
              </div>
            </div>
          </div>
        </div>

        <footer class="modal-footer" style="gap: 0.75rem;">
          <button class="btn-secondary" style="border-radius: 100px; padding: 0.5rem 1.25rem;" (click)="close.emit()">Cancelar</button>
          <button class="btn-primary" [style.background]="confirmColor" style="border:none; border-radius: 100px; padding: 0.5rem 1.25rem;" (click)="onConfirm()">Confirmar</button>
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
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  `]
})
export class ConfirmationModalComponent implements OnInit, OnChanges {
  @Input() message: string = '';
  @Input() symbol: string = '';
  @Input() side: string = '';
  @Input() livePrice: number = 0;
  @Input() sl: number = 0;
  @Input() tp: number = 0;
  @Input() quantity: number = 0.1;
  @Input() confirmColor: string = '';
  
  @Output() close = new EventEmitter<void>();
  @Output() confirm = new EventEmitter<{sl: number, tp: number, quantity: number}>();

  editableSl: number = 0;
  editableTp: number = 0;
  editableQuantity: number = 0.1;
  userEdited: boolean = false;

  ngOnInit() {
    this.editableSl = this.sl;
    this.editableTp = this.tp;
    this.editableQuantity = this.quantity;
  }

  ngOnChanges(changes: SimpleChanges) {
    if (!this.userEdited) {
      if (changes['sl']) this.editableSl = changes['sl'].currentValue;
      if (changes['tp']) this.editableTp = changes['tp'].currentValue;
    }
    if (changes['quantity']) {
      this.editableQuantity = changes['quantity'].currentValue;
    }
  }

  onEdit() {
    this.userEdited = true;
  }

  onConfirm() {
    this.confirm.emit({ sl: this.editableSl, tp: this.editableTp, quantity: this.editableQuantity });
  }

  calculateProfit(): number {
    if (this.side === 'BUY') {
      return (this.editableTp - this.livePrice) * this.editableQuantity;
    } else {
      return (this.livePrice - this.editableTp) * this.editableQuantity;
    }
  }

  calculateLoss(): number {
    if (this.side === 'BUY') {
      return (this.livePrice - this.editableSl) * this.editableQuantity;
    } else {
      return (this.editableSl - this.livePrice) * this.editableQuantity;
    }
  }
}
