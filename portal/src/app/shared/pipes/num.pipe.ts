import { Pipe, PipeTransform } from '@angular/core';

/** Formatea un número sin sufijo (para cantidades de activos). */
@Pipe({ name: 'num' })
export class NumPipe implements PipeTransform {
  transform(value: number | null | undefined, digits = 8): string {
    if (value == null || Number.isNaN(value)) return '—';
    return new Intl.NumberFormat('es-ES', {
      maximumFractionDigits: digits,
    }).format(value);
  }
}
