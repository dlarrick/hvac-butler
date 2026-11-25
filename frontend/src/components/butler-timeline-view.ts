import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { JournalEntry } from '../types';
import {
  ALL_SPACES_ID,
  formatShortTimestamp,
  formatStreakRange,
  formatTriggerLabel,
  groupTimelineItems
} from '../utils/timeline';

@customElement('butler-timeline-view')
export class ButlerTimelineView extends LitElement {
  @property({ attribute: false }) entries: JournalEntry[] = [];
  @property({ type: String }) selectedSpaceId = '';

  @state() private _expandedStreaks: Set<string> = new Set();

  static styles = css`
    :host {
      display: block;
    }

    .empty-state {
      padding: 24px 12px;
      text-align: center;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 0.9rem;
    }

    .timeline {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .row {
      display: flex;
      flex-direction: column;
      gap: 5px;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      background: var(--secondary-background-color, rgba(127, 127, 127, 0.06));
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease;
      text-align: left;
    }

    .row:hover {
      background: rgba(127, 127, 127, 0.14);
      border-color: var(--primary-color, #03a9f4);
    }

    .row.plan-anchor {
      border-left: 3px solid var(--primary-color, #03a9f4);
      background: rgba(3, 169, 244, 0.05);
    }

    .row.plan-anchor:hover {
      background: rgba(3, 169, 244, 0.11);
    }

    .row.unchanged-intraday {
      opacity: 0.8;
    }

    .row-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }

    .badges {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .badge-trigger-plan {
      background: rgba(3, 169, 244, 0.18);
      color: var(--primary-color, #29b6f6);
    }

    .badge-trigger-presence {
      background: rgba(156, 39, 176, 0.18);
      color: #ce93d8;
    }

    .badge-trigger-alarm {
      background: rgba(255, 152, 0, 0.18);
      color: #ffb74d;
    }

    .badge-adjusted {
      background: rgba(76, 175, 80, 0.18);
      color: #81c784;
    }

    .badge-boost {
      background: rgba(255, 112, 67, 0.2);
      color: #ff8a65;
    }

    .badge-fallback {
      background: rgba(255, 152, 0, 0.22);
      color: #ffb74d;
    }

    .badge-error {
      background: rgba(244, 67, 54, 0.2);
      color: #ef5350;
    }

    .time {
      font-size: 0.76rem;
      color: var(--secondary-text-color, #9e9e9e);
      white-space: nowrap;
    }

    .summary {
      font-size: 0.86rem;
      line-height: 1.4;
      color: var(--primary-text-color, #e1e1e1);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .collapsed-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 8px;
      border: 1px dashed var(--divider-color, rgba(255, 255, 255, 0.16));
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 0.8rem;
      cursor: pointer;
      user-select: none;
    }

    .collapsed-row:hover {
      background: rgba(127, 127, 127, 0.1);
      color: var(--primary-text-color, #e1e1e1);
    }

    .collapsed-left {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
    }

    .streak-children {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding-left: 12px;
      border-left: 2px solid var(--divider-color, rgba(255, 255, 255, 0.12));
    }
  `;

  private _toggleStreak(id: string): void {
    const next = new Set(this._expandedStreaks);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    this._expandedStreaks = next;
  }

  private _selectEntry(entry: JournalEntry): void {
    this.dispatchEvent(
      new CustomEvent('select-entry', {
        detail: { entry },
        bubbles: true,
        composed: true
      })
    );
  }

  private _triggerBadgeClass(entry: JournalEntry): string {
    const t = entry.trigger?.type;
    if (t === 'presence_change') return 'badge-trigger-presence';
    if (t === 'alarm_change') return 'badge-trigger-alarm';
    return 'badge-trigger-plan';
  }

  private _renderEntryRow(entry: JournalEntry) {
    const isAll = this.selectedSpaceId === ALL_SPACES_ID;
    const isPlan = entry.kind === 'plan';
    const allRecs = Object.values(entry.spaces || {});
    const rec = isAll ? undefined : entry.spaces?.[this.selectedSpaceId];

    const anyFallback = isAll
      ? allRecs.some((r) => r.fallback)
      : Boolean(rec?.fallback);
    const changedRecs = allRecs.filter((r) => r.changed);
    const anyChanged = isAll ? changedRecs.length > 0 : Boolean(rec?.changed);
    const anyBoost = isAll
      ? allRecs.some((r) => r.comfort_boost?.applied)
      : Boolean(rec?.comfort_boost?.applied);
    const isUnchangedIntraday = !isPlan && !anyChanged && !anyFallback && !anyBoost;

    let summaryText: string;
    if (!isAll) {
      summaryText = rec?.summary || entry.headline || 'No details recorded.';
    } else if (allRecs.length === 1) {
      summaryText = `${allRecs[0].name}: ${allRecs[0].summary}`;
    } else if (changedRecs.length === 1) {
      summaryText = `${changedRecs[0].name}: ${changedRecs[0].summary}`;
    } else {
      summaryText = entry.headline || 'No details recorded.';
    }

    return html`
      <div
        class="row ${isPlan ? 'plan-anchor' : ''} ${isUnchangedIntraday
          ? 'unchanged-intraday'
          : ''}"
        role="button"
        tabindex="0"
        @click=${() => this._selectEntry(entry)}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this._selectEntry(entry);
          }
        }}
      >
        <div class="row-top">
          <div class="badges">
            <span
              class="badge ${this._triggerBadgeClass(entry)}"
              title="Deterministic trigger that started this evaluation"
            >
              ${formatTriggerLabel(entry.trigger)}
            </span>
            ${entry.status === 'error'
              ? html`<span class="badge badge-error">Error</span>`
              : nothing}
            ${anyFallback
              ? html`<span class="badge badge-fallback">Fallback</span>`
              : anyChanged
                ? html`<span class="badge badge-adjusted">
                    ${isAll && changedRecs.length > 1
                      ? `${changedRecs.length} Adjusted`
                      : 'Adjusted'}
                  </span>`
                : nothing}
            ${anyBoost
              ? html`<span class="badge badge-boost">Comfort Boost</span>`
              : nothing}
          </div>
          <span class="time">${formatShortTimestamp(entry.timestamp)}</span>
        </div>
        <div class="summary">${summaryText}</div>
      </div>
    `;
  }

  render() {
    if (!this.selectedSpaceId) {
      return html`<div class="empty-state">No spaces configured in HVAC Butler.</div>`;
    }

    const isAll = this.selectedSpaceId === ALL_SPACES_ID;
    const spaceEntries = isAll
      ? this.entries
      : this.entries.filter(
          (e) => e.spaces && this.selectedSpaceId in e.spaces
        );

    if (spaceEntries.length === 0) {
      return html`
        <div class="empty-state">
          No activity recorded yet${isAll ? '' : ' for this space'}. Use
          <strong>Run Plan</strong> to generate a plan now.
        </div>
      `;
    }

    const items = groupTimelineItems(spaceEntries, this.selectedSpaceId);

    return html`
      <div class="timeline">
        ${items.map((item) => {
          if (item.type === 'entry') {
            return this._renderEntryRow(item.entry);
          }
          const expanded = this._expandedStreaks.has(item.id);
          return html`
            <div
              class="collapsed-row"
              role="button"
              tabindex="0"
              @click=${() => this._toggleStreak(item.id)}
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  this._toggleStreak(item.id);
                }
              }}
            >
              <span class="collapsed-left">
                <span>${expanded ? '▾' : '▸'}</span>
                <span>${item.entries.length} unchanged checks</span>
              </span>
              <span class="time">${formatStreakRange(item.entries)}</span>
            </div>
            ${expanded
              ? html`
                  <div class="streak-children">
                    ${item.entries.map((e) => this._renderEntryRow(e))}
                  </div>
                `
              : nothing}
          `;
        })}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'butler-timeline-view': ButlerTimelineView;
  }
}
