import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private apiUrl = environment.apiUrl;
  constructor(private http: HttpClient) {}

  getTrades(skip = 0, limit = 10, status = '', startDate = '', endDate = ''): Observable<any> {
    let url = `${this.apiUrl}/trades/?skip=${skip}&limit=${limit}`;
    if (status)    url += `&status=${status}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate)   url += `&end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getBotStatus():                   Observable<any>    { return this.http.get<any>(`${this.apiUrl}/status/bot`); }
  getBalance():                     Observable<any>    { return this.http.get<any>(`${this.apiUrl}/balance/`); }
  getPriceLogs(skip=0, limit=100):  Observable<any>    { return this.http.get<any>(`${this.apiUrl}/status/prices?skip=${skip}&limit=${limit}`); }
  analyzeWithAI(data: any):         Observable<any>    { return this.http.post<any>(`${this.apiUrl}/ai/analyze`, data); }

  // ── Stats ──────────────────────────────────────────────────────────────────
  getStatsSummary():                Observable<any>    { return this.http.get<any>(`${this.apiUrl}/stats/summary`); }
  getPnLOverTime(days = 30):        Observable<any>    { return this.http.get<any>(`${this.apiUrl}/stats/pnl-over-time?days=${days}`); }
  getRsiDistribution():             Observable<any>    { return this.http.get<any>(`${this.apiUrl}/stats/rsi-distribution`); }
  getHealth():                      Observable<any>    { return this.http.get<any>(`${this.apiUrl}/stats/health`); }
}
