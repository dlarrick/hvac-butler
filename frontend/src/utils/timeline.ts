import type {
  JournalEntry,
  JournalSpaceRecord,
  JournalTrigger,
  ScheduleBlock,
  WeatherSnapshot
} from '../types';

export const ALL_SPACES_ID = '__all__';

export type TimelineItem =
  | { type: 'entry'; entry: JournalEntry }
  | { type: 'collapsed'; id: string; entries: JournalEntry[] };

/**
 * Determine whether an intraday entry is an unchanged check for the selected space
 * (or across all spaces when ALL_SPACES_ID is selected).
 * Plan entries ("keyframes") are never collapsible.
 */
export function isCollapsibleUnchanged(
  entry: JournalEntry,
  spaceId: string
): boolean {
  if (entry.kind === 'plan') return false;
  if (entry.status === 'error' || entry.status === 'fallback' || entry.heuristic) {
    return false;
  }
  if (spaceId === ALL_SPACES_ID) {
    const records = Object.values(entry.spaces || {});
    if (records.length === 0) return true;
    return records.every(
      (rec) => !rec.changed && !rec.fallback && !rec.locked && !rec.comfort_boost?.applied
    );
  }
  const rec = entry.spaces?.[spaceId];
  if (!rec) return false;
  if (rec.changed || rec.fallback || rec.locked) return false;
  if (rec.comfort_boost?.applied) return false;
  return true;
}

/**
 * Group newest-first entries for a space:
 * - Plan entries always stay visible as standalone daily anchors ("keyframes").
 * - Consecutive chains of 2+ unchanged intraday checks collapse into a single expandable row.
 */
export function groupTimelineItems(
  entries: JournalEntry[],
  spaceId: string
): TimelineItem[] {
  const items: TimelineItem[] = [];
  let streak: JournalEntry[] = [];

  const flushStreak = () => {
    if (streak.length === 0) return;
    if (streak.length === 1) {
      items.push({ type: 'entry', entry: streak[0] });
    } else {
      items.push({
        type: 'collapsed',
        id: `streak_${streak[0].id}_${streak[streak.length - 1].id}`,
        entries: [...streak]
      });
    }
    streak = [];
  };

  for (const entry of entries) {
    if (isCollapsibleUnchanged(entry, spaceId)) {
      streak.push(entry);
    } else {
      flushStreak();
      items.push({ type: 'entry', entry });
    }
  }
  flushStreak();

  return items;
}

export function formatShortTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  const timeStr = date.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit'
  });

  if (sameDay) {
    return `Today ${timeStr}`;
  }

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate();

  if (isYesterday) {
    return `Yesterday ${timeStr}`;
  }

  const dayStr = date.toLocaleDateString([], { weekday: 'short' });
  return `${dayStr} ${timeStr}`;
}

export function formatFullTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
}

export function formatStreakRange(entries: JournalEntry[]): string {
  if (entries.length === 0) return '';
  // entries are newest-first
  const newest = entries[0].timestamp;
  const oldest = entries[entries.length - 1].timestamp;
  return `${formatShortTimestamp(oldest)} – ${formatShortTimestamp(newest)}`;
}

export function formatTriggerLabel(trigger?: JournalTrigger): string {
  if (!trigger) return 'Event';
  if (trigger.label) return trigger.label;
  switch (trigger.type) {
    case 'scheduled_plan':
    case 'manual_plan':
      return 'Plan';
    case 'presence_change':
      return 'Presence';
    case 'alarm_change':
      return 'Arm/Disarm';
    case 'manual_intraday':
      return 'Manual Check';
    default:
      return trigger.type.replace(/_/g, ' ');
  }
}

export function formatTriggerDetail(trigger?: JournalTrigger): string {
  if (!trigger) return '';
  if (trigger.type === 'manual_plan') {
    return 'Triggered manually (Run Plan)';
  }
  if (trigger.type === 'manual_intraday') {
    return 'Triggered manually (Check Now)';
  }
  if (trigger.type === 'scheduled_plan') {
    return 'Scheduled nightly macro-plan';
  }
  if (trigger.type === 'presence_change') {
    const sensor = trigger.sensor || 'presence sensor';
    const to = trigger.to || trigger.state || '?';
    const transition = trigger.from ? `${trigger.from} → ${to}` : `→ ${to}`;
    const dur = trigger.for_minutes ? ` (${trigger.for_minutes}m)` : '';
    return `Triggered by ${sensor} ${transition}${dur}`;
  }
  if (trigger.type === 'alarm_change') {
    const from = trigger.from || '?';
    const to = trigger.to || '?';
    return `Triggered by alarm ${from} → ${to}`;
  }
  return `Triggered by ${trigger.type}`;
}

export function formatWeatherSummary(weather?: WeatherSnapshot | null): string {
  if (!weather) return '';
  const parts: string[] = [];
  const cur = weather.current;
  if (cur && cur.temperature != null) {
    const cond = cur.condition ? ` ${cur.condition}` : '';
    const wind = cur.wind_speed != null ? `, ${Math.round(cur.wind_speed)} mph wind` : '';
    parts.push(`Now ${Math.round(cur.temperature)}°F${cond}${wind}`);
  }
  const tom = weather.tomorrow_daily;
  if (tom && (tom.temp_low != null || tom.temp_high != null)) {
    const low = tom.temp_low != null ? `${Math.round(tom.temp_low)}°` : '?';
    const high = tom.temp_high != null ? `${Math.round(tom.temp_high)}°F` : '?';
    const cond = tom.condition ? ` ${tom.condition}` : '';
    parts.push(`Tomorrow ${low}–${high}${cond}`);
  }
  return parts.join(' · ');
}

function trimSeconds(timeStr: string): string {
  if (!timeStr) return '';
  if (timeStr.startsWith('23:59:59')) return '24:00';
  const parts = timeStr.split(':');
  if (parts.length >= 2) {
    return `${parts[0]}:${parts[1]}`;
  }
  return timeStr;
}

export function formatBlockLine(block: ScheduleBlock): string {
  const from = trimSeconds(block.from);
  const to = trimSeconds(block.to);
  const d = block.data || {};
  const mode = String(d.hvac_mode || 'heat_cool').toLowerCase();
  if (mode === 'off') {
    return `${from}–${to}  Off`;
  }
  if (mode === 'heat' && d.heat_to != null) {
    return `${from}–${to}  Heat ${d.heat_to}°F`;
  }
  if (mode === 'cool' && d.cool_to != null) {
    return `${from}–${to}  Cool ${d.cool_to}°F`;
  }
  if (d.heat_to != null && d.cool_to != null) {
    return `${from}–${to}  ${d.heat_to}°–${d.cool_to}°F`;
  }
  return `${from}–${to}  ${mode}`;
}

export interface DayBlockDiff {
  day: string;
  before: ScheduleBlock[];
  after: ScheduleBlock[];
}

export function computeChangedDays(rec: JournalSpaceRecord): DayBlockDiff[] {
  const beforeMap = rec.before_blocks || {};
  const afterMap = rec.after_blocks || {};
  const days = Array.from(new Set([...Object.keys(beforeMap), ...Object.keys(afterMap)]));
  const diffs: DayBlockDiff[] = [];

  for (const day of days) {
    const b = beforeMap[day] || [];
    const a = afterMap[day] || [];
    if (JSON.stringify(b) !== JSON.stringify(a)) {
      diffs.push({ day, before: b, after: a });
    }
  }
  return diffs;
}

export function capitalize(str: string): string {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}
