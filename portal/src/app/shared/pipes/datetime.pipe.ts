import { Pipe, PipeTransform } from '@angular/core';

/** Formatea una fecha ISO a local (dd/mm/aaaa hh:mm:ss). */
@Pipe({ name: 'fecha' })
export class DateTimePipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('es-ES', {
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(date);
  }
}
