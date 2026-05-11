import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) { }

  getTrades(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/trades`);
  }

  getPriceLogs(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/price-logs`);
  }

  getBotStatus(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/bot-status`);
  }

  getBalance(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/balance`);
  }
}
