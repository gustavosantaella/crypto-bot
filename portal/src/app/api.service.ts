import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) { }

  getTrades(skip: number = 0, limit: number = 10, status: string = ''): Observable<any> {
    const statusParam = status ? `&status=${status}` : '';
    return this.http.get<any>(`${this.apiUrl}/trades?skip=${skip}&limit=${limit}${statusParam}`);
  }

  getPriceLogs(skip: number = 0, limit: number = 15): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/price-logs?skip=${skip}&limit=${limit}`);
  }

  getBotStatus(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/bot-status`);
  }

  getBalance(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/balance`);
  }
}
