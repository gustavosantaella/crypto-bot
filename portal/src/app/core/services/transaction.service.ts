import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Transaction } from '../models/transaction.model';
import { TransactionStats } from '../models/transaction-stats.model';

export interface TransactionFilters {
  testMode?: boolean | null;
  status?: string | null;
  limit?: number;
  offset?: number;
}

@Injectable({ providedIn: 'root' })
export class TransactionService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/transactions`;

  getStats(testMode?: boolean): Observable<TransactionStats> {
    let params = new HttpParams();
    if (testMode != null) {
      params = params.set('test_mode', String(testMode));
    }
    return this.http.get<TransactionStats>(`${this.baseUrl}/stats`, { params });
  }

  list(filters: TransactionFilters = {}): Observable<Transaction[]> {
    let params = new HttpParams();
    if (filters.testMode != null) {
      params = params.set('test_mode', String(filters.testMode));
    }
    if (filters.status) {
      params = params.set('status', filters.status);
    }
    params = params.set('limit', String(filters.limit ?? 100));
    params = params.set('offset', String(filters.offset ?? 0));
    return this.http.get<Transaction[]>(this.baseUrl, { params });
  }

  get(id: number): Observable<Transaction> {
    return this.http.get<Transaction>(`${this.baseUrl}/${id}`);
  }
}
