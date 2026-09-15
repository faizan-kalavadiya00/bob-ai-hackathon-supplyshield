import { request } from './shared';

export interface RecoveryStep {
  id: string;
  action: string;
  description: string;
  estimated_cost_usd: number;
  time_to_implement_days: number;
  rri_improvement: number;
  impact_score: number;
  status: 'pending' | 'in_progress' | 'completed' | 'rejected';
}

export interface RecoveryPlan {
  plan_id: string;
  disruption_id?: string;
  shipment_id?: string;
  total_cost_usd: number;
  total_rri_improvement: number;
  steps: RecoveryStep[];
  created_at: string;
}

export const recoveryApi = {
  getPlanByDisruption: (disruptionId: string) => 
    request<RecoveryPlan>(`/api/recovery/${disruptionId}`),
  getPlanByShipment: (shipmentId: string) => 
    request<RecoveryPlan>(`/api/recovery/shipment/${shipmentId}`),
};
