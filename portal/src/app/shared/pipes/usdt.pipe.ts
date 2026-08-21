import { Pipe, PipeTransform } from '@angular/core';

/** Formatea un valor numérico como USDT (ej. 1.234,56 USDT). */
@Pipe({ name: 'usdt' })
export class UsdtPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    if (value == null || Number.isNaN(value)) return '—';
    return new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8,
    }).format(value) + ' USDT';
  }
}
