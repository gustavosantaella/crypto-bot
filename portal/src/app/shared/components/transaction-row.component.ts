import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Transaction } from '../../core/models/transaction.model';
import { DateTimePipe } from '../../shared/pipes/datetime.pipe';
import { PercentPipe } from '../../shared/pipes/percent.pipe';
import { UsdtPipe } from '../../shared/pipes/usdt.pipe';

@Component({
  selector: 'app-transaction-row',
  standalone: true,
  imports: [RouterLink, UsdtPipe, PercentPipe, DateTimePipe],
  template: `
    <td class="cell cell--id">
      <a [routerLink]="['/transactions', tx().id]">#{{ tx().id }}</a>
    </td>
    <td class="cell">{{ tx().symbol }}</td>
    <td class="cell">
      <span class="badge" [class.badge--spot]="tx().market_type === 'SPOT'"
                         [class.badge--futures]="tx().market_type === 'FUTURES'">
        {{ tx().market_type }}
      </span>
    </td>
    <td class="cell">
      <span class="badge" [class.badge--long]="tx().side === 'LONG'"
                         [class.badge--short]="tx().side === 'SHORT'">
        {{ tx().side }}{{ tx().leverage > 1 ? ' ' + tx().leverage + '×' : '' }}
      </span>
    </td>
    <td class="cell">
      <span class="badge" [class.badge--open]="tx().status === 'OPEN'"
                         [class.badge--closed]="tx().status === 'CLOSED'"
                         [class.badge--canceled]="tx().status === 'CANCELED'">
        {{ tx().status }}
      </span>
    </td>
    <td class="cell">
      <span class="badge" [class.badge--test]="tx().test_mode" [class.badge--real]="!tx().test_mode">
        {{ tx().test_mode ? 'TEST' : 'REAL' }}
      </span>
    </td>
    <td class="cell cell--num">{{ tx().buy_price | usdt }}</td>
    <td class="cell">{{ tx().buy_time | fecha }}</td>
    <td class="cell cell--num">{{ tx().sell_price != null ? (tx().sell_price | usdt) : '—' }}</td>
    <td class="cell">{{ tx().sell_time != null ? (tx().sell_time | fecha) : '—' }}</td>
    <td class="cell cell--num" [class.text--profit]="(tx().profit ?? 0) > 0"
                              [class.text--loss]="(tx().profit ?? 0) < 0">
      {{ tx().profit != null ? (tx().profit | usdt) : '—' }}
    </td>
    <td class="cell cell--num" [class.text--profit]="(tx().profit_pct ?? 0) > 0"
                              [class.text--loss]="(tx().profit_pct ?? 0) < 0">
      {{ tx().profit_pct != null ? (tx().profit_pct | pct) : '—' }}
    </td>
  `,
  styles: [`
    :host { display: contents; }
    .cell { padding: 0.7rem 0.9rem; white-space: nowrap; }
    .cell--id a { color: var(--accent); text-decoration: none; font-weight: 600; }
    .cell--id a:hover { text-decoration: underline; }
    .cell--num { text-align: right; font-variant-numeric: tabular-nums; }
    .badge { padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.03em; }
    .badge--open { background: var(--warn-bg); color: var(--warn); }
    .badge--closed { background: var(--ok-bg); color: var(--ok); }
    .badge--canceled { background: var(--danger-bg); color: var(--danger); }
    .badge--test { background: rgba(148, 163, 184, 0.18); color: #94a3b8; }
    .badge--real { background: rgba(34, 211, 238, 0.15); color: #22d3ee; }
    .badge--spot { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
    .badge--futures { background: rgba(168, 85, 247, 0.16); color: #a78bfa; }
    .badge--long { background: var(--ok-bg); color: var(--ok); }
    .badge--short { background: var(--danger-bg); color: var(--danger); }
    .text--profit { color: var(--ok); }
    .text--loss { color: var(--danger); }
  `],
})
export class TransactionRowComponent {
  tx = input.required<Transaction>();
}
