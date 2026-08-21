import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Order } from '../models/order.model';

@Injectable({ providedIn: 'root' })
export class OrderService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/orders`;

  list(symbol?: string, side?: string, testMode?: boolean, limit = 100): Observable<Order[]> {
    let params = new HttpParams().set('limit', String(limit));
    if (symbol) params = params.set('symbol', symbol);
    if (side) params = params.set('side', side);
    if (testMode != null) params = params.set('test_mode', String(testMode));
    return this.http.get<Order[]>(this.baseUrl, { params });
  }
}
