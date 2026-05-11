import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = 'http://localhost:8000/api/v1';

  constructor(private http: HttpClient) { }

  getTrades(skip: number = 0, limit: number = 10, status: string = '', startDate: string = '', endDate: string = ''): Observable<any> {
    let url = `${this.apiUrl}/trades/?skip=${skip}&limit=${limit}`;
    if (status) url += `&status=${status}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getPriceLogs(skip: number = 0, limit: number = 15, startDate: string = '', endDate: string = ''): Observable<any> {
    let url = `${this.apiUrl}/status/prices?skip=${skip}&limit=${limit}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    return this.http.get<any>(url);
  }

  getBotStatus(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/status/bot`);
  }

  getBalance(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/balance/`);
  }
}
