import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type {
  BriefCommitResponse,
  BriefingMessage,
  BriefTurnResponse,
  HomeAssistant
} from '../types';
import { BUTLER_HEAD_DATA_URI } from '../assets/butler-head';

function greetingForHour(hour: number): string {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

@customElement('butler-brief-modal')
export class ButlerBriefModal extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;

  @state() private _messages: BriefingMessage[] = [];
  @state() private _pendingActions: Record<string, unknown>[] = [];
  @state() private _draft = '';
  @state() private _sending = false;
  @state() private _committing = false;
  @state() private _error: string | null = null;

  static styles = css`
    :host {
      position: fixed;
      inset: 0;
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 12px;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(2px);
      box-sizing: border-box;
    }

    .dialog {
      width: min(560px, 100%);
      max-height: min(82vh, 640px);
      display: flex;
      flex-direction: column;
      background: var(--card-background-color, #1c1c1c);
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.14));
      border-radius: 14px;
      box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55);
      overflow: hidden;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }

    .header-avatar {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      flex-shrink: 0;
      border: 1px solid rgba(255, 255, 255, 0.18);
    }

    .header-titles {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .header-title {
      font-size: 0.98rem;
      font-weight: 700;
      line-height: 1.2;
    }

    .header-sub {
      font-size: 0.74rem;
      color: var(--secondary-text-color, #9e9e9e);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9e9e9e);
      font-size: 1.3rem;
      line-height: 1;
      cursor: pointer;
      padding: 4px 6px;
      border-radius: 6px;
    }

    .close-btn:hover {
      background: rgba(127, 127, 127, 0.18);
      color: var(--primary-text-color, #fff);
    }

    .messages {
      flex: 1 1 auto;
      overflow-y: auto;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 180px;
    }

    .msg-row {
      display: flex;
      align-items: flex-end;
      gap: 8px;
    }

    .msg-row.user {
      justify-content: flex-end;
    }

    .msg-avatar {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      flex-shrink: 0;
      border: 1px solid rgba(255, 255, 255, 0.14);
    }

    .bubble {
      max-width: 84%;
      padding: 8px 11px;
      border-radius: 12px;
      font-size: 0.86rem;
      line-height: 1.42;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .msg-row.assistant .bubble {
      background: var(--secondary-background-color, rgba(255, 255, 255, 0.07));
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.09));
      border-bottom-left-radius: 4px;
    }

    .msg-row.user .bubble {
      background: rgba(3, 169, 244, 0.2);
      border: 1px solid rgba(3, 169, 244, 0.35);
      border-bottom-right-radius: 4px;
    }

    .typing {
      color: var(--secondary-text-color, #9e9e9e);
      font-style: italic;
    }

    .error-banner {
      margin: 0 14px 8px;
      padding: 8px 10px;
      border-radius: 8px;
      background: rgba(244, 67, 54, 0.14);
      color: var(--error-color, #ef5350);
      font-size: 0.8rem;
    }

    .composer {
      display: flex;
      align-items: flex-end;
      gap: 8px;
      padding: 10px 14px;
      border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
    }

    textarea {
      flex: 1 1 auto;
      resize: none;
      background: var(--secondary-background-color, rgba(255, 255, 255, 0.06));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.18));
      border-radius: 10px;
      padding: 8px 10px;
      font-size: 0.86rem;
      font-family: inherit;
      line-height: 1.35;
      min-height: 38px;
      max-height: 110px;
      box-sizing: border-box;
    }

    textarea:focus {
      outline: none;
      border-color: var(--primary-color, #03a9f4);
    }

    .send-btn {
      background: var(--secondary-background-color, rgba(255, 255, 255, 0.1));
      color: var(--primary-text-color, #e1e1e1);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.22));
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.82rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
      white-space: nowrap;
    }

    .send-btn:hover:not(:disabled) {
      background: rgba(127, 127, 127, 0.22);
    }

    .send-btn:disabled {
      opacity: 0.45;
      cursor: default;
    }

    .footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 14px;
      border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      background: rgba(0, 0, 0, 0.14);
    }

    .cancel-btn {
      background: transparent;
      color: var(--secondary-text-color, #bdbdbd);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.2));
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 0.82rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
    }

    .cancel-btn:hover:not(:disabled) {
      background: rgba(127, 127, 127, 0.16);
      color: var(--primary-text-color, #fff);
    }

    .done-btn {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border: none;
      border-radius: 8px;
      padding: 6px 16px;
      font-size: 0.84rem;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
    }

    .done-btn:hover:not(:disabled) {
      opacity: 0.92;
    }

    .done-btn:disabled,
    .cancel-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener('keydown', this._handleKeydown);
    if (this._messages.length === 0) {
      const greeting = greetingForHour(new Date().getHours());
      this._messages = [
        {
          role: 'assistant',
          content: `${greeting}! Tell me about any upcoming guests, events, travel, or schedule changes—I'll ask any quick HVAC questions and note them on my calendar.`
        }
      ];
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this._handleKeydown);
  }

  private _handleKeydown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape' && !this._committing) {
      this._cancel();
    }
  };

  private _cancel(): void {
    this.dispatchEvent(
      new CustomEvent('close-brief', { bubbles: true, composed: true })
    );
  }

  private _scrollToBottom(): void {
    void this.updateComplete.then(() => {
      const el = this.renderRoot.querySelector('.messages');
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    });
  }

  private async _send(): Promise<void> {
    const text = this._draft.trim();
    if (!text || !this.hass || this._sending || this._committing) return;

    const nextMessages: BriefingMessage[] = [
      ...this._messages,
      { role: 'user', content: text }
    ];
    this._messages = nextMessages;
    this._draft = '';
    this._error = null;
    this._sending = true;
    this._scrollToBottom();

    try {
      const resp = await this.hass.callWS<BriefTurnResponse>({
        type: 'hvac_butler/brief',
        messages: nextMessages
      });
      this._messages = [
        ...nextMessages,
        { role: 'assistant', content: resp.reply || 'Noted.' }
      ];
      if (Array.isArray(resp.calendar_actions) && resp.calendar_actions.length > 0) {
        this._pendingActions = resp.calendar_actions;
      }
      this._scrollToBottom();
    } catch (err) {
      this._error =
        err instanceof Error
          ? err.message
          : (err as { message?: string })?.message || 'Failed to reach HVAC Butler.';
    } finally {
      this._sending = false;
    }
  }

  private async _done(): Promise<void> {
    if (this._committing || this._sending) return;

    const pendingText = this._draft.trim();
    const finalMessages: BriefingMessage[] = pendingText
      ? [...this._messages, { role: 'user', content: pendingText }]
      : [...this._messages];

    const hasUserMessage = finalMessages.some((m) => m.role === 'user');
    if (!hasUserMessage || !this.hass) {
      this._cancel();
      return;
    }

    // If the user typed a new message right before hitting Done, clear stale actions
    // so the backend runs a fresh finalize pass incorporating that last message.
    const actionsToSend = pendingText ? [] : this._pendingActions;

    this._messages = finalMessages;
    this._draft = '';
    this._error = null;
    this._committing = true;

    try {
      const resp = await this.hass.callWS<BriefCommitResponse>({
        type: 'hvac_butler/brief_commit',
        messages: finalMessages,
        calendar_actions: actionsToSend
      });
      this.dispatchEvent(
        new CustomEvent('brief-committed', {
          detail: resp,
          bubbles: true,
          composed: true
        })
      );
      this._cancel();
    } catch (err) {
      this._error =
        err instanceof Error
          ? err.message
          : (err as { message?: string })?.message ||
            'Failed to save calendar notes.';
      this._committing = false;
    }
  }

  render() {
    const busy = this._sending || this._committing;

    return html`
      <div
        class="dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Call Butler"
        @click=${(e: Event) => e.stopPropagation()}
      >
        <div class="header">
          <div class="header-left">
            <img class="header-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />
            <div class="header-titles">
              <span class="header-title">Call Butler</span>
              <span class="header-sub">
                Discuss upcoming events for Butler's calendar
              </span>
            </div>
          </div>
          <button
            class="close-btn"
            aria-label="Close"
            ?disabled=${this._committing}
            @click=${this._cancel}
          >
            &times;
          </button>
        </div>

        <div class="messages">
          ${this._messages.map(
            (m) => html`
              <div class="msg-row ${m.role}">
                ${m.role === 'assistant'
                  ? html`<img class="msg-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />`
                  : nothing}
                <div class="bubble">${m.content}</div>
              </div>
            `
          )}
          ${this._sending
            ? html`
                <div class="msg-row assistant">
                  <img class="msg-avatar" src=${BUTLER_HEAD_DATA_URI} alt="" />
                  <div class="bubble typing">Thinking…</div>
                </div>
              `
            : nothing}
        </div>

        ${this._error ? html`<div class="error-banner">${this._error}</div>` : nothing}

        <div class="composer">
          <textarea
            rows="2"
            placeholder="Tell the butler about upcoming events that affect the home's climate controls."
            .value=${this._draft}
            ?disabled=${busy}
            @input=${(e: Event) => {
              this._draft = (e.target as HTMLTextAreaElement).value;
            }}
            @keydown=${(e: KeyboardEvent) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void this._send();
              }
            }}
          ></textarea>
          <button
            class="send-btn"
            ?disabled=${busy || !this._draft.trim()}
            @click=${() => void this._send()}
          >
            Send
          </button>
        </div>

        <div class="footer">
          <button
            class="cancel-btn"
            ?disabled=${this._committing}
            @click=${this._cancel}
          >
            Cancel
          </button>
          <button
            class="done-btn"
            ?disabled=${busy}
            @click=${() => void this._done()}
          >
            ${this._committing ? 'Saving…' : 'Done'}
          </button>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'butler-brief-modal': ButlerBriefModal;
  }
}
