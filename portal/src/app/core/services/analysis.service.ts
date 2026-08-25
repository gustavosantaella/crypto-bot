import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { MarketAnalysis } from '../models/market-analysis.model';
import { MarketType } from '../models/transaction.model';

/** Señal de mercado (LONG/SHORT/NEUTRAL) calculada por la API. */
@Injectable({ providedIn: 'root' })
export class AnalysisService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/analysis`;

  getSignal(
    testMode: boolean,
    marketType: MarketType = 'SPOT',
    interval = '1m',
  ): Observable<MarketAnalysis> {
    const params = new HttpParams()
      .set('test_mode', String(testMode))
      .set('market_type', marketType)
      .set('interval', interval);
    return this.http.get<MarketAnalysis>(`${this.baseUrl}/signal`, { params });
  }
}
