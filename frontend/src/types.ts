export interface HomeAssistantConnection {
  subscribeEvents<T = unknown>(
    callback: (ev: T) => void,
    eventType?: string
  ): Promise<() => void>;
  addEventListener?(event: string, callback: () => void): void;
  removeEventListener?(event: string, callback: () => void): void;
}

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  connection?: HomeAssistantConnection;
  callWS<T = unknown>(msg: Record<string, unknown>): Promise<T>;
  callService(
    domain: string,
    service: string,
    serviceData?: Record<string, unknown>
  ): Promise<unknown>;
}

export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
  last_changed: string;
  last_updated: string;
}

export interface ScheduleBlockData {
  hvac_mode?: string;
  heat_to?: number;
  cool_to?: number;
  [key: string]: unknown;
}

export interface ScheduleBlock {
  from: string;
  to: string;
  data?: ScheduleBlockData;
}

export interface ComfortBoostRecord {
  feeling: 'too_cold' | 'too_hot' | string;
  delta_f: number;
  duration_minutes: number;
  applied?: boolean;
}

export interface JournalSpaceRecord {
  name: string;
  changed: boolean;
  summary: string;
  fallback?: boolean;
  locked?: boolean;
  comfort_boost?: ComfortBoostRecord | null;
  guardrail_notes?: string[];
  before_blocks?: Record<string, ScheduleBlock[]>;
  after_blocks?: Record<string, ScheduleBlock[]>;
}

export interface JournalTrigger {
  type: 'scheduled_plan' | 'manual_plan' | 'presence_change' | 'alarm_change' | string;
  label: string;
  manual?: boolean;
  space_id?: string;
  sensor?: string;
  state?: string;
  for_minutes?: number;
  from?: string;
  to?: string;
  [key: string]: unknown;
}

export interface WeatherSnapshot {
  current?: {
    temperature?: number | null;
    condition?: string | null;
    wind_speed?: number | null;
  };
  tomorrow_daily?: {
    date?: string;
    condition?: string | null;
    temp_high?: number | null;
    temp_low?: number | null;
    wind_speed?: number | null;
    precipitation_probability?: number | null;
  };
  periods?: Record<
    string,
    {
      temp_min?: number | null;
      temp_max?: number | null;
      wind_max?: number | null;
      conditions?: string[];
    }
  >;
}

export interface JournalEntry {
  schema_version: number;
  id: string;
  timestamp: string;
  kind: 'plan' | 'intraday';
  status: 'ok' | 'fallback' | 'error' | string;
  trigger: JournalTrigger;
  target_days?: string[];
  weather_snapshot?: WeatherSnapshot | null;
  headline?: string;
  error?: string | null;
  spaces: Record<string, JournalSpaceRecord>;
  raw_response?: unknown;
}

export interface ButlerSpaceSummary {
  space_id: string;
  name: string;
  climate_entity: string;
  butler_schedule?: string | null;
  default_mode: string;
  active_preset?: string | null;
  locked?: boolean;
}

export interface JournalResponse {
  status: string;
  last_nightly_run: string | null;
  last_intraday_run: string | null;
  last_error: string | null;
  spaces: ButlerSpaceSummary[];
  entries: JournalEntry[];
}

export interface HvacButlerCardConfig {
  type: string;
  entity?: string;
  title?: string;
  space_id?: string;
  limit?: number;
}

export interface BriefingMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface BriefTurnResponse {
  reply: string;
  ready_to_commit: boolean;
  calendar_actions: Record<string, unknown>[];
}

export interface BriefCommitResponse {
  committed: {
    added: number;
    updated: number;
    deleted: number;
  };
  summary_reply?: string;
  triggered_reeval?: boolean;
}
