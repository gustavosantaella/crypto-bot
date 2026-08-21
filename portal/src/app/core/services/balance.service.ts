import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AccountBalance } from '../models/balance.model';

@Injectable({ providedIn: 'root' })
export class BalanceService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/balance`;

  get(): Observable<AccountBalance> {
    return this.http.get<AccountBalance>(this.baseUrl);
  }
}
