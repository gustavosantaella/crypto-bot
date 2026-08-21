import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AccountBalance } from '../models/balance.model';

@Injectable({ providedIn: 'root' })
export class BalanceService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/balance`;

  /** Balance spot del ambiente indicado (true=testnet, false=producción). */
  get(testMode: boolean): Observable<AccountBalance> {
    const params = new HttpParams().set('test_mode', String(testMode));
    return this.http.get<AccountBalance>(this.baseUrl, { params });
  }
}
