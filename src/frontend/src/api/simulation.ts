import { request } from './shared';

export interface SimulationParams {
  type: string;
  severity: string;
  region: string;
  duration_days: number;
}

export interface SimulationMetrics {
  on_time_delivery_rate: number;
  cost_impact_usd: number;
  disrupted_shipments: number;
  average_delay_days: number;
}

export interface SimulationResult {
  scenario_id: string;
  before: SimulationMetrics;
  after: SimulationMetrics;
  insights: string[];
}

export const simulationApi = {
  getHistory: () => request<SimulationResult[]>('/api/simulation'),
  simulate: (params: SimulationParams) => 
    request<SimulationResult>('/api/simulation', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};
