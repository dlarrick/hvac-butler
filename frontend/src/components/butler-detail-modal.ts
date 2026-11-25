import { LitElement, html, css, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { JournalEntry, JournalSpaceRecord } from '../types';
import {
  ALL_SPACES_ID,
  capitalize,
  computeChangedDays,
  formatBlockLine,
  formatFullTimestamp,
  formatTriggerDetail,
  formatTriggerLabel,
  formatWeatherSummary
} from '../utils/timeline';

@customElement('butler-detail-modal')
export class ButlerDetailModal extends LitElement {
  @property({ attribute: false }) entry: JournalEntry | null = null;
  @property({ type: String }) selectedSpaceId = '';

  static styles = css`
    :host {
      position: fixed;
      inset: 0;
      z-index: 999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      background: rgba(0, 0, 0, 0.55);
      backdrop-filter: blur(2px);
      box-sizing: border-box;
    }

    .dialog {
      background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
      border-radius: 14px;
      width: 100%;
      max-width: 600px;
      max-height: 82vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
      overflow: hidden;
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      min-width: 0;
    }

    .timestamp {
      font-size: 0.92rem;
      font-weight: 600;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 1.4rem;
      line-height: 1;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
    }

    .close-btn:hover {
      background: rgba(127, 127, 127, 0.18);
      color: var(--primary-text-color, #fff);
    }

    .modal-body {
      padding: 16px 18px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .context-strip {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 0.82rem;
      color: var(--secondary-text-color, #9e9e9e);
      background: rgba(127, 127, 127, 0.08);
      padding: 8px 12px;
      border-radius: 8px;
    }

    .error-banner {
      background: rgba(244, 67, 54, 0.14);
      border: 1px solid rgba(244, 67, 54, 0.35);
      color: var(--error-color, #ef5350);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
    }

    .section-label {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--secondary-text-color, #9e9e9e);
      margin-bottom: 6px;
    }

    .featured-space {
      border: 1px solid var(--primary-color, #03a9f4);
      background: rgba(3, 169, 244, 0.06);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .space-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }

    .space-name {
      font-weight: 600;
      font-size: 0.96rem;
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

    .badge-unchanged {
      background: rgba(127, 127, 127, 0.16);
      color: var(--secondary-text-color, #9e9e9e);
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

    .summary-text {
      font-size: 0.9rem;
      line-height: 1.48;
      margin: 0;
    }

    .boost-detail {
      font-size: 0.82rem;
      color: #ff8a65;
      background: rgba(255, 112, 67, 0.1);
      padding: 6px 10px;
      border-radius: 6px;
    }

    .diff-box {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 2px;
    }

    .diff-day {
      background: rgba(127, 127, 127, 0.08);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 0.8rem;
    }

    .diff-day-title {
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--primary-text-color, #e1e1e1);
    }

    .diff-columns {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    @media (max-width: 500px) {
      .diff-columns {
        grid-template-columns: 1fr;
      }
    }

    .diff-col-label {
      font-size: 0.72rem;
      color: var(--secondary-text-color, #9e9e9e);
      margin-bottom: 3px;
    }

    .diff-line {
      font-family: var(--code-font-family, monospace);
      font-size: 0.76rem;
      line-height: 1.4;
    }

    .other-spaces-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .other-space-item {
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .other-space-item.unchanged {
      opacity: 0.88;
    }

    details.accordion {
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.84rem;
    }

    details.accordion summary {
      cursor: pointer;
      color: var(--secondary-text-color, #9e9e9e);
      font-weight: 500;
      user-select: none;
    }

    details.accordion[open] summary {
      margin-bottom: 8px;
    }

    .guardrail-list {
      margin: 0 0 8px 0;
      padding-left: 18px;
      font-size: 0.8rem;
      color: #ffb74d;
    }

    pre.raw-json {
      margin: 0;
      padding: 10px;
      border-radius: 6px;
      background: rgba(0, 0, 0, 0.25);
      font-size: 0.74rem;
      overflow-x: auto;
      max-height: 220px;
      white-space: pre-wrap;
      word-break: break-word;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener('keydown', this._handleKeyDown);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this._handleKeyDown);
  }

  private _handleKeyDown = (ev: KeyboardEvent): void => {
    if (ev.key === 'Escape') {
      this._close();
    }
  };

  private _handleBackdropClick(ev: MouseEvent): void {
    if (ev.target === ev.currentTarget) {
      this._close();
    }
  }

  private _close(): void {
    this.dispatchEvent(new CustomEvent('close-modal', { bubbles: true, composed: true }));
  }

  private _triggerBadgeClass(entry: JournalEntry): string {
    const t = entry.trigger?.type;
    if (t === 'presence_change') return 'badge-trigger-presence';
    if (t === 'alarm_change') return 'badge-trigger-alarm';
    return 'badge-trigger-plan';
  }

  private _renderSpaceBadges(rec: JournalSpaceRecord) {
    return html`
      <div class="badges">
        ${rec.locked
          ? html`<span class="badge badge-fallback">Edit Locked</span>`
          : nothing}
        ${rec.fallback
          ? html`<span class="badge badge-fallback">Fallback</span>`
          : rec.changed
            ? html`<span class="badge badge-adjusted">Adjusted</span>`
            : html`<span class="badge badge-unchanged">Unchanged</span>`}
        ${rec.comfort_boost
          ? html`<span class="badge badge-boost">Comfort Boost</span>`
          : nothing}
      </div>
    `;
  }

  private _renderSpaceDiff(rec: JournalSpaceRecord) {
    const diffs = computeChangedDays(rec);
    if (diffs.length === 0) return nothing;
    return html`
      <div class="diff-box">
        ${diffs.map(
          (d) => html`
            <div class="diff-day">
              <div class="diff-day-title">${capitalize(d.day)} schedule</div>
              <div class="diff-columns">
                <div>
                  <div class="diff-col-label">Before</div>
                  ${d.before.length
                    ? d.before.map(
                        (b) => html`<div class="diff-line">${formatBlockLine(b)}</div>`
                      )
                    : html`<div class="diff-line">(none)</div>`}
                </div>
                <div>
                  <div class="diff-col-label">After</div>
                  ${d.after.length
                    ? d.after.map(
                        (b) => html`<div class="diff-line">${formatBlockLine(b)}</div>`
                      )
                    : html`<div class="diff-line">(none)</div>`}
                </div>
              </div>
            </div>
          `
        )}
      </div>
    `;
  }

  private _renderOtherSpaceItem(rec: JournalSpaceRecord) {
    return html`
      <div class="other-space-item ${rec.changed ? '' : 'unchanged'}">
        <div class="space-header">
          <span class="space-name">${rec.name}</span>
          ${this._renderSpaceBadges(rec)}
        </div>
        <p class="summary-text">${rec.summary}</p>
        ${rec.changed ? this._renderSpaceDiff(rec) : nothing}
      </div>
    `;
  }

  render() {
    const entry = this.entry;
    if (!entry) return nothing;

    const spacesMap = entry.spaces || {};
    const isAll = this.selectedSpaceId === ALL_SPACES_ID;
    const selectedRec =
      !isAll && this.selectedSpaceId ? spacesMap[this.selectedSpaceId] : undefined;
    const otherEntries = Object.entries(spacesMap).filter(
      ([sid]) => isAll || sid !== this.selectedSpaceId
    );
    const otherChanged = otherEntries.filter(([, r]) => r.changed || r.fallback);
    const otherUnchanged = otherEntries.filter(([, r]) => !r.changed && !r.fallback);

    const weatherLine = formatWeatherSummary(entry.weather_snapshot);
    const triggerDetail = formatTriggerDetail(entry.trigger);

    const allGuardrailNotes: string[] = [];
    for (const [, rec] of Object.entries(spacesMap)) {
      for (const note of rec.guardrail_notes || []) {
        allGuardrailNotes.push(`${rec.name}: ${note}`);
      }
    }

    return html`
      <div class="dialog" @click=${(e: Event) => e.stopPropagation()}>
        <div class="modal-header">
          <div class="header-left">
            <span class="badge ${this._triggerBadgeClass(entry)}">
              ${formatTriggerLabel(entry.trigger)}
            </span>
            ${entry.status === 'error'
              ? html`<span class="badge badge-error">Error</span>`
              : nothing}
            <span class="timestamp">${formatFullTimestamp(entry.timestamp)}</span>
          </div>
          <button
            class="close-btn"
            @click=${this._close}
            aria-label="Close details"
            title="Close"
          >
            ×
          </button>
        </div>

        <div class="modal-body">
          <div class="context-strip">
            <div>${triggerDetail}</div>
            ${weatherLine ? html`<div>${weatherLine}</div>` : nothing}
          </div>

          ${entry.error
            ? html`<div class="error-banner">${entry.error}</div>`
            : nothing}

          ${selectedRec
            ? html`
                <div>
                  <div class="section-label">Selected Space</div>
                  <div class="featured-space">
                    <div class="space-header">
                      <span class="space-name">${selectedRec.name}</span>
                      ${this._renderSpaceBadges(selectedRec)}
                    </div>
                    <p class="summary-text">${selectedRec.summary}</p>
                    ${selectedRec.comfort_boost
                      ? html`
                          <div class="boost-detail">
                            Comfort Boost:
                            ${selectedRec.comfort_boost.feeling === 'too_cold' ? '+' : '-'}
                            ${selectedRec.comfort_boost.delta_f}°F
                            (${selectedRec.comfort_boost.duration_minutes}m)
                            ${selectedRec.comfort_boost.applied
                              ? '— applied'
                              : '— not applied (space not on Butler preset)'}
                          </div>
                        `
                      : nothing}
                    ${this._renderSpaceDiff(selectedRec)}
                  </div>
                </div>
              `
            : nothing}

          ${otherEntries.length > 0
            ? html`
                <div>
                  <div class="section-label">
                    ${selectedRec ? 'Other Spaces in This Evaluation' : 'Spaces'}
                  </div>
                  <div class="other-spaces-list">
                    ${otherChanged.map(([, rec]) => this._renderOtherSpaceItem(rec))}
                    ${otherUnchanged.length > (selectedRec ? 3 : 4)
                      ? html`
                          <details class="accordion">
                            <summary>
                              ${selectedRec ? 'Other unchanged spaces' : 'Unchanged spaces'}
                              (${otherUnchanged.length})
                            </summary>
                            <div class="other-spaces-list">
                              ${otherUnchanged.map(([, rec]) =>
                                this._renderOtherSpaceItem(rec)
                              )}
                            </div>
                          </details>
                        `
                      : otherUnchanged.map(([, rec]) =>
                          this._renderOtherSpaceItem(rec)
                        )}
                  </div>
                </div>
              `
            : nothing}

          <details class="accordion">
            <summary>Technical details</summary>
            ${allGuardrailNotes.length > 0
              ? html`
                  <div class="section-label">Guardrail Notes</div>
                  <ul class="guardrail-list">
                    ${allGuardrailNotes.map((n) => html`<li>${n}</li>`)}
                  </ul>
                `
              : nothing}
            <div class="section-label">
              Record v${entry.schema_version ?? 1} · Raw AI Output
            </div>
            <pre class="raw-json">${JSON.stringify(entry.raw_response ?? null, null, 2)}</pre>
          </details>
        </div>
      </div>
    `;
  }

  firstUpdated(): void {
    this.addEventListener('click', (ev) => this._handleBackdropClick(ev));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'butler-detail-modal': ButlerDetailModal;
  }
}
