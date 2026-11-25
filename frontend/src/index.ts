/**
 * HVAC Butler Lovelace Dashboard Card
 *
 * Registers `custom:hvac-butler-card` — space-scoped activity timeline of
 * daily plans and intraday evaluations with full AI context detail modal.
 */

import './hvac-butler-card';

export * from './types';

(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: 'hvac-butler-card',
  name: 'HVAC Butler Activity Card',
  description:
    'Space-scoped timeline of HVAC Butler daily plans and intraday evaluations with full AI commentary and schedule diffs.',
  preview: true,
  getEntitySuggestion: (hass: any, entityId: string) => {
    const attrs = hass?.states?.[entityId]?.attributes;
    if (
      !entityId.startsWith('sensor.') ||
      !attrs ||
      (attrs.butler_schedules === undefined &&
        attrs.space_summaries === undefined &&
        attrs.space_explanations === undefined)
    ) {
      return null;
    }
    return {
      config: {
        type: 'custom:hvac-butler-card',
        entity: entityId
      }
    };
  }
});
