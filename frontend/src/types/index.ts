// ──────────────────────────────────────────────────────────────────────────────
// Plant
// ──────────────────────────────────────────────────────────────────────────────
export interface Plant {
  id: number;
  name: string;
  location: string;
  country: string;
  installed_dc_capacity_mw: number;
  installed_ac_capacity_mw: number;
  commission_date: string;
  number_of_blocks: number;
  inverter_type: string;
  number_of_inverters: number;
  panel_manufacturer: string;
  panel_model: string;
  total_panel_area_sqm: number;
  module_efficiency: number;
  daily_running_hours: number;
  annual_degradation_rate: number;
  expected_pr: number;
  expected_cuf: number;
  expected_availability: number;
  grid_operator: string;
  timezone: string;
  has_weather_station: boolean;
  has_string_monitoring: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface PlantCreate {
  name: string;
  location: string;
  country: string;
  installed_dc_capacity_mw: number;
  installed_ac_capacity_mw: number;
  commission_date: string;
  number_of_blocks: number;
  inverter_type: 'central' | 'string';
  number_of_inverters: number;
  panel_manufacturer: string;
  panel_model: string;
  total_panel_area_sqm: number;
  module_efficiency: number;
  daily_running_hours: number;
  annual_degradation_rate: number;
  expected_pr: number;
  expected_cuf: number;
  expected_availability: number;
  grid_operator: string;
  timezone: string;
  has_weather_station: boolean;
  has_string_monitoring: boolean;
  notes?: string;
}

export interface PlantUpdate {
  name?: string;
  location?: string;
  country?: string;
  installed_dc_capacity_mw?: number;
  installed_ac_capacity_mw?: number;
  commission_date?: string;
  number_of_blocks?: number;
  inverter_type?: 'central' | 'string';
  number_of_inverters?: number;
  panel_manufacturer?: string;
  panel_model?: string;
  total_panel_area_sqm?: number;
  module_efficiency?: number;
  daily_running_hours?: number;
  annual_degradation_rate?: number;
  expected_pr?: number;
  expected_cuf?: number;
  expected_availability?: number;
  grid_operator?: string;
  timezone?: string;
  has_weather_station?: boolean;
  has_string_monitoring?: boolean;
  notes?: string;
}

export interface PlantListItem {
  id: number;
  name: string;
  location: string;
  installed_dc_capacity_mw: number;
  commission_date: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Dashboard
// ──────────────────────────────────────────────────────────────────────────────
export interface DashboardSummary {
  total_generation_kwh: number;
  possible_generation_kwh: number;
  performance_ratio: number;
  cuf: number;
  availability: number;
  loss_percentage: number;
  health_score: number;
  degradation_index: number;
  generation_trend: GenerationDataPoint[];
  loss_breakdown: LossCategory[];
  recent_alerts: Alert[];
  top_recommendations: Recommendation[];
}

export interface GenerationDataPoint {
  date: string;
  actual_kwh: number;
  expected_kwh: number;
  pr?: number;
  cuf?: number;
  irradiation?: number;
  specific_yield?: number;
}

export interface LossCategory {
  category: string;
  value: number;
  color: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Generation
// ──────────────────────────────────────────────────────────────────────────────
export interface GenerationData {
  period: string;
  data: GenerationDataPoint[];
  total_actual_kwh: number;
  total_expected_kwh: number;
  average_pr: number;
}

// ──────────────────────────────────────────────────────────────────────────────
// Inverter
// ──────────────────────────────────────────────────────────────────────────────
export interface InverterSummary {
  inverter_id: string;
  name: string;
  capacity_kw: number;
  total_generation_kwh: number;
  performance_ratio: number;
  availability: number;
  status: 'healthy' | 'warning' | 'critical' | 'offline';
  efficiency: number;
  specific_yield?: number;
  machine_loss_kwh?: number;
}

// ──────────────────────────────────────────────────────────────────────────────
// Loss
// ──────────────────────────────────────────────────────────────────────────────
export interface LossDataPoint {
  date: string;
  grid_failure_kwh: number;
  curtailment_kwh: number;
  machine_loss_kwh: number;
  total_loss_kwh: number;
}

export interface LossBreakdown {
  total_loss_kwh: number;
  total_loss_percentage: number;
  categories: LossDetail[];
  time_series: LossDataPoint[];
}

export interface LossDetail {
  category: string;
  loss_kwh: number;
  loss_percentage: number;
  description: string;
  color: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Inverter
// ──────────────────────────────────────────────────────────────────────────────
export interface InverterSummary {
  inverter_id: string;
  name: string;
  capacity_kw: number;
  total_generation_kwh: number;
  performance_ratio: number;
  availability: number;
  status: 'healthy' | 'warning' | 'critical' | 'offline';
  efficiency: number;
  specific_yield?: number;
  machine_loss_kwh?: number;
}

export interface InverterTimeSeriesPoint {
  date: string;
  inverter_name: string;
  generation_kwh: number;
  pr: number;
  specific_yield: number;
  machine_loss_kwh: number;
}

export interface InverterResponse {
  summaries: InverterSummary[];
  time_series: InverterTimeSeriesPoint[];
}

// ──────────────────────────────────────────────────────────────────────────────
// Degradation
// ──────────────────────────────────────────────────────────────────────────────
export interface DegradationData {
  annual_degradation_rate: number;
  cumulative_degradation: number;
  expected_lifetime_years: number;
  expected_degradation: number;
  trend: DegradationDataPoint[];
}

export interface DegradationDataPoint {
  year: string;
  pr: number;
  expected_pr: number;
}

// ──────────────────────────────────────────────────────────────────────────────
// Irradiation
// ──────────────────────────────────────────────────────────────────────────────
export interface IrradiationDataPoint {
  date: string;
  ghi_kwh_m2: number;
  poa_kwh_m2: number;
  peak_sun_hours: number;
}

export interface IrradiationData {
  plant_id: number;
  total_ghi_kwh_m2: number;
  total_poa_kwh_m2: number;
  average_daily_ghi: number;
  average_daily_poa: number;
  peak_sun_hours: number;
  data: IrradiationDataPoint[];
}

// ──────────────────────────────────────────────────────────────────────────────
// Import
// ──────────────────────────────────────────────────────────────────────────────
export interface ImportConfig {
  plant_id: number;
  import_type: 'generation' | 'irradiation' | 'inverter' | 'weather';
  file_name: string;
  file_size: number;
}

export interface ImportValidationResult {
  is_valid: boolean;
  total_rows: number;
  valid_rows: number;
  errors: ValidationError[];
  warnings: string[];
}

export interface ValidationError {
  row: number;
  column: string;
  message: string;
  value: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Alert
// ──────────────────────────────────────────────────────────────────────────────
export interface Alert {
  id: number;
  plant_id: number;
  severity: 'info' | 'warning' | 'critical';
  title?: string;
  message: string;
  category: string;
  status: string;
  resolved_date?: string;
  is_read?: boolean;
  created_at: string;
  updated_at: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Recommendation
// ──────────────────────────────────────────────────────────────────────────────
export interface Recommendation {
  id: number;
  plant_id: number;
  priority: 'low' | 'medium' | 'high';
  title?: string;
  description: string;
  category: string;
  potential_gain_kwh?: number;
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed';
  generated_date: string;
  created_at: string;
  updated_at: string;
}
// ──────────────────────────────────────────────────────────────────────────────
// Report
// ──────────────────────────────────────────────────────────────────────────────
export interface Report {
  id: number;
  plant_id: number;
  report_type: 'daily' | 'weekly' | 'monthly' | 'annual' | 'custom';
  title: string;
  file_path: string;
  generated_at: string;
  period_start: string;
  period_end: string;
  status: 'generating' | 'completed' | 'failed';
}

// ──────────────────────────────────────────────────────────────────────────────
// Daily Record Manual Input
// ──────────────────────────────────────────────────────────────────────────────
export interface DailyRecordInput {
  record_date: string;
  generation_kwh: number;
  irradiation_wh_m2: number;
  inverter_id?: number;
  grid_failure_kwh?: number;
  curtailment_kwh?: number;
  grid_loss_kwh?: number;
  machine_loss_kwh?: number;
}

export interface DailyRecordInputResponse {
  success: boolean;
  message: string;
  records_updated: number;
  record_date: string;
}

export interface FinancialLosses {
  tariff_per_kwh: number;
  currency: string;
  total_revenue_lost: number;
  grid_loss_revenue: number;
  machine_loss_revenue: number;
  curtailment_revenue: number;
  realized_revenue: number;
  potential_total_revenue: number;
}

