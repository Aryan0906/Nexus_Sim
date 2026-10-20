import React from 'react';
import { ENDPOINTS } from '../config/api';

interface EmissionsResult {
  agent_type: string;
  distance_km: number;
  idle_minutes: number;
  co2_g: number;
  nox_g: number;
  pm_g: number;
}

const PANEL_TITLE_STYLE: React.CSSProperties = {
  fontSize: '12px',
  fontWeight: 700,
  color: '#e5e7eb',
  marginBottom: '8px',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
};

const LABEL_STYLE: React.CSSProperties = {
  fontSize: '10px',
  color: '#9ca3af',
  marginBottom: '3px',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
};

const INPUT_STYLE: React.CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  borderRadius: '6px',
  border: '1px solid #374151',
  backgroundColor: 'rgba(15, 23, 42, 0.8)',
  color: '#e5e7eb',
  fontSize: '12px',
  fontFamily: 'system-ui, sans-serif',
  boxSizing: 'border-box',
};

const BTN_STYLE: React.CSSProperties = {
  width: '100%',
  padding: '7px',
  borderRadius: '6px',
  border: 'none',
  backgroundColor: '#059669',
  color: '#ffffff',
  fontSize: '12px',
  fontWeight: 700,
  cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif',
};

const METRIC_STYLE: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '4px 0',
  fontSize: '12px',
  color: '#d1d5db',
  borderBottom: '1px solid rgba(55, 65, 81, 0.4)',
};

/**
 * Emissions & Carbon Accounting panel (docs/futureplanning.md Phase 5).
 * Estimates CO2 / NOx / PM for a single agent via the public gateway endpoint.
 */
export const EmissionsPanel: React.FC = () => {
  const [agentType, setAgentType] = React.useState<string>('car');
  const [distanceKm, setDistanceKm] = React.useState<string>('100');
  const [idleMinutes, setIdleMinutes] = React.useState<string>('10');
  const [result, setResult] = React.useState<EmissionsResult | null>(null);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  const estimate = async () => {
    setLoading(true);
    setError(null);
    try {
      const form = new URLSearchParams({
        agent_type: agentType,
        distance_km: distanceKm,
        idle_minutes: idleMinutes,
      });
      const res = await fetch(ENDPOINTS.EMISSIONS_ESTIMATE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={PANEL_TITLE_STYLE}>🌱 Emissions & Carbon</div>

      <div style={{ marginBottom: '8px' }}>
        <div style={LABEL_STYLE}>Agent Type</div>
        <select
          value={agentType}
          onChange={(e) => setAgentType(e.target.value)}
          style={INPUT_STYLE}
        >
          <option value="car">Car (ICE)</option>
          <option value="bus">Bus (ICE)</option>
          <option value="ev">EV</option>
          <option value="truck">Truck (ICE)</option>
        </select>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <div style={LABEL_STYLE}>Distance (km)</div>
        <input
          type="number"
          min="0"
          step="1"
          value={distanceKm}
          onChange={(e) => setDistanceKm(e.target.value)}
          style={INPUT_STYLE}
        />
      </div>

      <div style={{ marginBottom: '8px' }}>
        <div style={LABEL_STYLE}>Idle Minutes</div>
        <input
          type="number"
          min="0"
          step="0.5"
          value={idleMinutes}
          onChange={(e) => setIdleMinutes(e.target.value)}
          style={INPUT_STYLE}
        />
      </div>

      <button onClick={estimate} disabled={loading} style={BTN_STYLE}>
        {loading ? 'Estimating…' : 'Estimate Emissions'}
      </button>

      {error && (
        <div style={{ marginTop: '8px', fontSize: '11px', color: '#f87171' }}>
          Error: {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: '10px' }}>
          <div style={METRIC_STYLE}>
            <span>CO₂</span>
            <span style={{ color: '#34d399', fontWeight: 700 }}>
              {result.co2_g.toFixed(1)} g
            </span>
          </div>
          <div style={METRIC_STYLE}>
            <span>NOx</span>
            <span style={{ color: '#fbbf24', fontWeight: 700 }}>
              {result.nox_g.toFixed(4)} g
            </span>
          </div>
          <div style={METRIC_STYLE}>
            <span>PM₂.₅</span>
            <span style={{ color: '#f87171', fontWeight: 700 }}>
              {result.pm_g.toFixed(4)} g
            </span>
          </div>
          <div style={{ marginTop: '6px', fontSize: '10px', color: '#6b7280' }}>
            Over {result.distance_km} km with {result.idle_minutes} min idling
            ({result.agent_type}).
          </div>
        </div>
      )}
    </div>
  );
};

export default EmissionsPanel;
