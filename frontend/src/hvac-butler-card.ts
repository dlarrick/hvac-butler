import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type {
  ButlerSpaceSummary,
  HomeAssistant,
  HomeAssistantConnection,
  HvacButlerCardConfig,
  JournalEntry,
  JournalResponse
} from './types';
import './components/butler-timeline-view';
import './components/butler-detail-modal';
import './components/butler-brief-modal';
import { BUTLER_HEAD_DATA_URI } from './assets/butler-head';
import { ALL_SPACES_ID } from './utils/timeline';

const STORAGE_KEY_SELECTED_SPACE = 'hvac_butler_card_selected_space';
const BUTLER_UPDATED_EVENT = 'hvac_butler_updated';
const STARTUP_RETRY_DELAYS_MS = [2000, 3000, 5000, 8000, 10000];

@customElement('hvac-butler-card')
export class HvacButlerCard extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;

  @state() private _config: HvacButlerCardConfig = { type: 'custom:hvac-butler-card' };
  @state() private _status = 'idle';
  @state() private _spaces: ButlerSpaceSummary[] = [];
  @state() private _entries: JournalEntry[] = [];
  @state() private _latestPlan: JournalEntry | null = null;
  @state() private _selectedSpaceId = '';
  @state() private _selectedEntry: JournalEntry | null = null;
  @state() private _showBriefModal = false;
  @state() private _loading = true;
  @state() private _reconnecting = false;
  @state() private _runningPlan = false;
  @state() private _error: string | null = null;

  private _lastWatchedFingerprint = '';
  private _fetching = false;
  private _pendingRefetch = false;
  private _unsubUpdatedEvent: (() => void) | null = null;
  private _subscribing = false;
  private _boundConnection: HomeAssistantConnection | null = null;
  private _retryAttempt = 0;
  private _retryTimer: number | null = null;

  static styles = css`
    :host {
      display: block;
    }

    ha-card {
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px 8px;
      flex-wrap: wrap;
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--primary-text-color, #e1e1e1);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      font-size: 0.74rem;
      font-weight: 600;
      padding: 2px 9px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .status-ok {
      background: rgba(52, 211, 153, 0.14);
      color: #34d399;
      border: 1px solid rgba(52, 211, 153, 0.35);
    }

    .status-busy {
      background: rgba(56, 189, 248, 0.16);
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.35);
    }

    .status-fallback {
      background: rgba(251, 191, 36, 0.14);
      color: #fbbf24;
      border: 1px solid rgba(251, 191, 36, 0.35);
    }

    .status-error {
      background: rgba(244, 67, 54, 0.16);
      color: #f87171;
      border: 1px solid rgba(244, 67, 54, 0.35);
    }

    .status-idle {
      background: rgba(127, 127, 127, 0.14);
      color: var(--secondary-text-color, #9e9e9e);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .header-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      width: 100%;
    }

    .call-butler-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.06);
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.2));
      border-radius: 999px;
      padding: 3px 10px 3px 4px;
      font-size: 0.78rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: background 0.15s ease, border-color 0.15s ease;
    }

    .call-butler-btn:hover {
      background: rgba(3, 169, 244, 0.14);
      border-color: rgba(3, 169, 244, 0.45);
    }

    .call-butler-avatar {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      display: block;
    }

    .controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: nowrap;
      min-width: 0;
      width: 100%;
    }

    .space-select {
      background: var(--secondary-background-color, rgba(127, 127, 127, 0.12));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.16));
      border-radius: 8px;
      padding: 4px 8px;
      font-size: 0.8rem;
      font-family: inherit;
      cursor: pointer;
      min-width: 0;
      flex: 1 1 auto;
      text-overflow: ellipsis;
    }

    .run-btn {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border: none;
      border-radius: 8px;
      padding: 5px 10px;
      font-size: 0.78rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: opacity 0.15s ease;
    }

    .run-btn:hover:not(:disabled) {
      opacity: 0.9;
    }

    .run-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    .check-btn {
      background: transparent;
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.22));
      border-radius: 8px;
      padding: 4px 9px;
      font-size: 0.78rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: background 0.15s ease, opacity 0.15s ease;
    }

    .check-btn:hover:not(:disabled) {
      background: rgba(127, 127, 127, 0.14);
    }

    .check-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    .space-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.78rem;
      color: var(--secondary-text-color, #9e9e9e);
      margin-top: -4px;
    }

    .error-msg {
      padding: 10px 12px;
      border-radius: 8px;
      background: rgba(244, 67, 54, 0.14);
      color: var(--error-color, #ef5350);
      font-size: 0.85rem;
    }

    .loading {
      padding: 20px 0;
      text-align: center;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 0.88rem;
    }
  `;

  static getStubConfig(): HvacButlerCardConfig {
    return {
      type: 'custom:hvac-butler-card',
      title: 'HVAC Butler'
    };
  }

  setConfig(config: HvacButlerCardConfig): void {
    this._config = {
      days: 2,
      ...config
    };
    if (config.space_id) {
      this._selectedSpaceId = config.space_id;
    }
  }

  getCardSize(): number {
    return 5;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._bindConnectionListener();
    void this._ensureSubscribed();
    void this._fetchJournal();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._clearRetryTimer();
    this._unbindConnectionListener();
    if (this._unsubUpdatedEvent) {
      this._unsubUpdatedEvent();
      this._unsubUpdatedEvent = null;
    }
  }

  protected updated(changedProps: Map<string, unknown>): void {
    if (changedProps.has('hass') && this.hass) {
      this._bindConnectionListener();
      void this._ensureSubscribed();
      const fp = this._computeWatchedFingerprint();
      if (fp !== this._lastWatchedFingerprint) {
        this._lastWatchedFingerprint = fp;
        void this._fetchJournal();
      }
    }
  }

  private _handleConnectionReady = (): void => {
    this._retryAttempt = 0;
    this._clearRetryTimer();
    if (this._unsubUpdatedEvent) {
      try {
        this._unsubUpdatedEvent();
      } catch {
        // ignore stale unsubscribe errors across reconnects
      }
      this._unsubUpdatedEvent = null;
    }
    void this._ensureSubscribed();
    void this._fetchJournal();
  };

  private _bindConnectionListener(): void {
    const conn = this.hass?.connection ?? null;
    if (conn === this._boundConnection) return;
    this._unbindConnectionListener();
    if (conn?.addEventListener) {
      conn.addEventListener('ready', this._handleConnectionReady);
      this._boundConnection = conn;
    }
  }

  private _unbindConnectionListener(): void {
    if (this._boundConnection?.removeEventListener) {
      this._boundConnection.removeEventListener('ready', this._handleConnectionReady);
    }
    this._boundConnection = null;
  }

  private _clearRetryTimer(): void {
    if (this._retryTimer !== null) {
      window.clearTimeout(this._retryTimer);
      this._retryTimer = null;
    }
  }

  private _isTransientStartupError(err: unknown): boolean {
    if (!err || typeof err !== 'object') return true;
    const code = (err as { code?: string }).code;
    if (code === 'unknown_command' || code === 'not_loaded') return true;
    const msg = String((err as { message?: string }).message || '').toLowerCase();
    return (
      msg.includes('not currently loaded') ||
      msg.includes('unknown command') ||
      msg.includes('connection') ||
      msg.includes('closed')
    );
  }

  private async _ensureSubscribed(): Promise<void> {
    if (
      this._unsubUpdatedEvent ||
      this._subscribing ||
      !this.hass?.connection?.subscribeEvents
    ) {
      return;
    }
    this._subscribing = true;
    try {
      const unsub = await this.hass.connection.subscribeEvents(() => {
        void this._fetchJournal();
      }, BUTLER_UPDATED_EVENT);
      if (!this.isConnected) {
        unsub();
      } else {
        this._unsubUpdatedEvent = unsub;
      }
    } catch {
      // Fall back to entity state fingerprint watching
    } finally {
      this._subscribing = false;
    }
  }

  private _computeWatchedFingerprint(): string {
    const states = this.hass?.states;
    if (!states) return '';
    const parts: string[] = [];
    for (const [eid, st] of Object.entries(states)) {
      if (!eid.startsWith('sensor.')) continue;
      const attrs = st.attributes || {};
      if (
        attrs.butler_schedules !== undefined ||
        attrs.space_summaries !== undefined ||
        attrs.space_explanations !== undefined
      ) {
        parts.push(`${eid}:${st.state}@${st.last_updated}`);
      }
    }
    return parts.sort().join('|');
  }

  private async _fetchJournal(): Promise<void> {
    if (!this.hass) return;
    if (this._fetching) {
      this._pendingRefetch = true;
      return;
    }
    this._fetching = true;
    try {
      const wsMsg: Record<string, unknown> = {
        type: 'hvac_butler/journal',
        days: this._config.days ?? 2
      };
      if (this._config.limit !== undefined) {
        wsMsg.limit = this._config.limit;
      }
      const resp = await this.hass.callWS<JournalResponse>(wsMsg);
      this._clearRetryTimer();
      this._retryAttempt = 0;
      this._reconnecting = false;
      this._status = resp.status || 'idle';
      this._spaces = resp.spaces || [];
      this._entries = resp.entries || [];
      this._latestPlan = resp.latest_plan ?? null;
      this._error = null;
      this._runningPlan = this._status === 'planning' || this._status === 'revising';

      // Resolve selected space: explicit config > saved preference > All spaces
      const validIds = new Set([
        ALL_SPACES_ID,
        ...this._spaces.map((s) => s.space_id)
      ]);
      if (!this._selectedSpaceId || !validIds.has(this._selectedSpaceId)) {
        const stored = this._readSavedSpace();
        if (this._config.space_id && validIds.has(this._config.space_id)) {
          this._selectedSpaceId = this._config.space_id;
        } else if (stored && validIds.has(stored)) {
          this._selectedSpaceId = stored;
        } else if (this._spaces.length > 0) {
          this._selectedSpaceId = ALL_SPACES_ID;
        }
      }
    } catch (err) {
      if (
        this._isTransientStartupError(err) &&
        this._retryAttempt < STARTUP_RETRY_DELAYS_MS.length
      ) {
        const delay = STARTUP_RETRY_DELAYS_MS[this._retryAttempt++];
        this._reconnecting = true;
        this._error = null;
        this._clearRetryTimer();
        this._retryTimer = window.setTimeout(() => {
          this._retryTimer = null;
          void this._fetchJournal();
        }, delay);
      } else {
        this._reconnecting = false;
        this._error =
          err instanceof Error
            ? err.message
            : (err as { message?: string })?.message ||
              'Unable to load HVAC Butler journal.';
      }
    } finally {
      if (!this._reconnecting) {
        this._loading = false;
      }
      this._fetching = false;
      if (this._pendingRefetch) {
        this._pendingRefetch = false;
        void this._fetchJournal();
      }
    }
  }

  private _readSavedSpace(): string {
    try {
      return window.localStorage.getItem(STORAGE_KEY_SELECTED_SPACE) || '';
    } catch {
      return '';
    }
  }

  private _saveSelectedSpace(spaceId: string): void {
    try {
      window.localStorage.setItem(STORAGE_KEY_SELECTED_SPACE, spaceId);
    } catch {
      // ignore storage quota / privacy mode errors
    }
  }

  private _handleSpaceChange(ev: Event): void {
    const select = ev.target as HTMLSelectElement;
    this._selectedSpaceId = select.value;
    this._saveSelectedSpace(select.value);
  }

  private async _handleRunPlan(): Promise<void> {
    if (!this.hass || this._runningPlan) return;
    this._runningPlan = true;
    this._status = 'planning';
    try {
      await this.hass.callWS({ type: 'hvac_butler/run_plan' });
    } catch (err) {
      this._error =
        err instanceof Error ? err.message : 'Failed to start nightly plan.';
      this._runningPlan = false;
    }
  }

  private async _handleRunIntraday(): Promise<void> {
    if (!this.hass || this._runningPlan) return;
    this._runningPlan = true;
    this._status = 'revising';
    try {
      const msg: Record<string, unknown> = { type: 'hvac_butler/run_intraday' };
      if (this._selectedSpaceId && this._selectedSpaceId !== ALL_SPACES_ID) {
        msg.space_id = this._selectedSpaceId;
      }
      await this.hass.callWS(msg);
    } catch (err) {
      this._error =
        err instanceof Error ? err.message : 'Failed to start intraday check.';
      this._runningPlan = false;
    }
  }

  private _statusPillInfo(): { label: string; cls: string } {
    switch (this._status) {
      case 'planning':
        return { label: 'Planning…', cls: 'status-busy' };
      case 'revising':
        return { label: 'Revising…', cls: 'status-busy' };
      case 'ok':
        return { label: 'OK', cls: 'status-ok' };
      case 'fallback':
        return { label: 'Fallback', cls: 'status-fallback' };
      case 'error':
        return { label: 'Error', cls: 'status-error' };
      default:
        return { label: 'Idle', cls: 'status-idle' };
    }
  }

  render() {
    const title = this._config.title || 'HVAC Butler';
    const pill = this._statusPillInfo();
    const activeSpace = this._spaces.find(
      (s) => s.space_id === this._selectedSpaceId
    );
    const isBusy =
      this._runningPlan ||
      this._status === 'planning' ||
      this._status === 'revising';

    return html`
      <ha-card>
        <div class="card-header">
          <div class="header-top">
            <div class="title-group">
              <span class="title">${title}</span>
              <span class="status-pill ${pill.cls}">${pill.label}</span>
            </div>
            <button
              class="call-butler-btn"
              @click=${() => {
                this._showBriefModal = true;
              }}
              title="Talk to HVAC Butler about upcoming events or schedule changes"
            >
              <img class="call-butler-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />
              <span>Call Butler</span>
            </button>
          </div>
          <div class="controls">
            ${this._spaces.length > 0
              ? html`
                  <select
                    class="space-select"
                    aria-label="Select space"
                    .value=${this._selectedSpaceId}
                    @change=${this._handleSpaceChange}
                  >
                    <option
                      value=${ALL_SPACES_ID}
                      ?selected=${this._selectedSpaceId === ALL_SPACES_ID}
                    >
                      All spaces
                    </option>
                    ${this._spaces.map(
                      (s) => html`
                        <option
                          value=${s.space_id}
                          ?selected=${s.space_id === this._selectedSpaceId}
                        >
                          ${s.name}
                        </option>
                      `
                    )}
                  </select>
                `
              : nothing}
            <button
              class="check-btn"
              ?disabled=${isBusy}
              @click=${this._handleRunIntraday}
              title="Run an immediate intraday presence & occupancy check"
            >
              Check Now
            </button>
            <button
              class="run-btn"
              ?disabled=${isBusy}
              @click=${this._handleRunPlan}
              title="Run macro-planner now for today and tomorrow"
            >
              ${isBusy ? 'Running…' : 'Run Plan'}
            </button>
          </div>
        </div>

        ${activeSpace?.active_preset
          ? html`
              <div class="space-meta">
                <span>
                  Active preset: <strong>${activeSpace.active_preset}</strong>
                  ${activeSpace.active_preset !== 'Butler' ? ' (Shadow mode)' : ''}
                </span>
              </div>
            `
          : nothing}

        ${this._error ? html`<div class="error-msg">${this._error}</div>` : nothing}

        ${this._loading
          ? html`
              <div class="loading">
                ${this._reconnecting
                  ? 'Connecting to HVAC Butler…'
                  : 'Loading Butler activity…'}
              </div>
            `
          : html`
              <butler-timeline-view
                .entries=${this._entries}
                .latestPlan=${this._latestPlan}
                .selectedSpaceId=${this._selectedSpaceId}
                @select-entry=${(e: CustomEvent<{ entry: JournalEntry }>) => {
                  this._selectedEntry = e.detail.entry;
                }}
              ></butler-timeline-view>
            `}
      </ha-card>

      ${this._selectedEntry
        ? html`
            <butler-detail-modal
              .entry=${this._selectedEntry}
              .selectedSpaceId=${this._selectedSpaceId}
              @close-modal=${() => {
                this._selectedEntry = null;
              }}
            ></butler-detail-modal>
          `
        : nothing}

      ${this._showBriefModal
        ? html`
            <butler-brief-modal
              .hass=${this.hass}
              @close-brief=${() => {
                this._showBriefModal = false;
              }}
              @brief-committed=${() => {
                void this._fetchJournal();
              }}
            ></butler-brief-modal>
          `
        : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'hvac-butler-card': HvacButlerCard;
  }
}
