import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AccountBalance } from '../models/balance.model';
import { MarketType } from '../models/transaction.model';

@Injectable({ providedIn: 'root' })
export class BalanceService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/balance`;

  /** Balance (y posiciones en futuros) del ambiente y mercado indicados. */
  get(testMode: boolean, marketType: MarketType = 'SPOT'): Observable<AccountBalance> {
    const params = new HttpParams()
      .set('test_mode', String(testMode))
      .set('market_type', marketType);
    return this.http.get<AccountBalance>(this.baseUrl, { params });
  }
}
