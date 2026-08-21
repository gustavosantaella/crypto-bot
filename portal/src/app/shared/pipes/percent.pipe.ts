import { Pipe, PipeTransform } from '@angular/core';

/** Formatea un porcentaje (ej. +1,49 %). */
@Pipe({ name: 'pct' })
export class PercentPipe implements PipeTransform {
  transform(value: number | null | undefined, digits = 2): string {
    if (value == null || Number.isNaN(value)) return '—';
    return `${value >= 0 ? '+' : ''}${value.toFixed(digits)} %`;
  }
}
