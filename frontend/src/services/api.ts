import axios, { type AxiosInstance, type AxiosResponse } from 'axios';
import type {
  Plant,
  PlantCreate,
  PlantUpdate,
  PlantListItem,
  DashboardSummary,
  GenerationData,
  InverterResponse,
  LossBreakdown,
  DegradationData,
  IrradiationData,
  Alert,
  Recommendation,
  Report,
  ImportValidationResult,
  DailyRecordInput,
  DailyRecordInputResponse,
} from '../types';


// ─── Axios Instance ──────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: (import.meta as any).env?.DEV ? 'http://localhost:8000/api' : '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Request Interceptor ────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    if ((import.meta as any).env?.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => {
    console.error('[API] Request Error:', error);
    return Promise.reject(error);
  },
);

// ─── Response Interceptor ───────────────────────────────────────────────────
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    if (error.response) {
      console.error(
        `[API] ${error.response.status} ${error.response.statusText}`,
        error.response.data,
      );
    } else if (error.request) {
      console.error('[API] No response received:', error.message);
    } else {
      console.error('[API] Error:', error.message);
    }
    return Promise.reject(error);
  },
);

// ─── Helper ─────────────────────────────────────────────────────────────────
const unwrap = <T>(res: AxiosResponse<T>): T => res.data;

// ─── Health ─────────────────────────────────────────────────────────────────
export const getHealth = (): Promise<{ status: string }> =>
  api.get('/health').then(unwrap);

// ─── Plants ─────────────────────────────────────────────────────────────────
export const getPlants = (): Promise<PlantListItem[]> =>
  api.get('/plants').then(unwrap);

export const getPlant = (id: number): Promise<Plant> =>
  api.get(`/plants/${id}`).then(unwrap);

export const createPlant = (data: PlantCreate): Promise<Plant> =>
  api.post('/plants', data).then(unwrap);

export const updatePlant = (id: number, data: PlantUpdate): Promise<Plant> =>
  api.put(`/plants/${id}`, data).then(unwrap);

export const deletePlant = (id: number): Promise<void> =>
  api.delete(`/plants/${id}`).then(unwrap);

// ─── Import ─────────────────────────────────────────────────────────────────
export const importData = (
  plantId: number,
  file: File,
  importType: string,
): Promise<ImportValidationResult> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('import_type', importType);
  return api
    .post(`/plants/${plantId}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120_000,
    })
    .then(unwrap);
};

// ─── Dashboard ──────────────────────────────────────────────────────────────
export const getDashboard = (plantId: number, startDate?: string, endDate?: string): Promise<DashboardSummary> =>
  api.get(`/plants/${plantId}/dashboard`, { params: { start_date: startDate, end_date: endDate } }).then(unwrap);

// ─── Generation ─────────────────────────────────────────────────────────────
export const getGeneration = (
  plantId: number,
  period: string,
  startDate?: string,
  endDate?: string,
): Promise<GenerationData> =>
  api.get(`/plants/${plantId}/generation`, { params: { period, start_date: startDate, end_date: endDate } }).then(unwrap);

// ─── KPI ────────────────────────────────────────────────────────────────────
export const getKPI = (plantId: number, startDate?: string, endDate?: string): Promise<Record<string, number>> =>
  api.get(`/plants/${plantId}/kpi`, { params: { start_date: startDate, end_date: endDate } }).then(unwrap);

// ─── Inverters ──────────────────────────────────────────────────────────────
export const getInverters = (plantId: number, period: string, startDate?: string, endDate?: string): Promise<InverterResponse> =>
  api.get(`/plants/${plantId}/inverters`, { params: { period, start_date: startDate, end_date: endDate } }).then(unwrap);

// ─── Losses ─────────────────────────────────────────────────────────────────
export const getLosses = (plantId: number, period: string, startDate?: string, endDate?: string): Promise<LossBreakdown> =>
  api.get(`/plants/${plantId}/losses`, { params: { period, start_date: startDate, end_date: endDate } }).then(unwrap);

// ─── Degradation ────────────────────────────────────────────────────────────
export const getDegradation = (plantId: number, period: string, startDate?: string, endDate?: string): Promise<DegradationData> =>
  api.get(`/plants/${plantId}/degradation`, { params: { period, start_date: startDate, end_date: endDate } }).then(unwrap);

// ─── Irradiation ────────────────────────────────────────────────────────────
export const getIrradiation = (plantId: number, period: string, startDate?: string, endDate?: string): Promise<IrradiationData> =>
  api.get(`/plants/${plantId}/irradiation`, { params: { period, start_date: startDate, end_date: endDate } }).then(unwrap);

// ─── Alerts ─────────────────────────────────────────────────────────────────
export const getAlerts = (
  plantId: number,
  severity?: string,
): Promise<Alert[]> =>
  api
    .get(`/plants/${plantId}/alerts`, { params: severity ? { severity } : {} })
    .then(unwrap);

// ─── Recommendations ────────────────────────────────────────────────────────
export const getRecommendations = (plantId: number): Promise<Recommendation[]> =>
  api.get(`/plants/${plantId}/recommendations`).then(unwrap);

// ─── Reports ────────────────────────────────────────────────────────────────
export const generateReport = (
  plantId: number,
  reportType: string,
  startDate?: string,
  endDate?: string,
): Promise<Report> =>
  api.post(`/plants/${plantId}/reports`, {
    report_type: reportType,
    start_date: startDate || null,
    end_date: endDate || null,
  }).then(unwrap);

export const getReports = (plantId: number): Promise<Report[]> =>
  api.get(`/plants/${plantId}/reports`).then(unwrap);

export const deleteReport = (plantId: number, reportId: number): Promise<{ success: boolean; message: string }> =>
  api.delete(`/plants/${plantId}/reports/${reportId}`).then(unwrap);

export const downloadReportFile = async (plantId: number, reportId: number, filename: string): Promise<void> => {
  const response = await api.get(`/plants/${plantId}/reports/${reportId}/download`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const openReport = (plantId: number, reportId: number): Promise<{ success: boolean; message: string }> =>
  api.post(`/plants/${plantId}/reports/${reportId}/open`).then(unwrap);

// ─── Daily Manual Entry & Management ────────────────────────────────────────
export const addDailyRecord = (
  plantId: number,
  data: DailyRecordInput,
): Promise<DailyRecordInputResponse> =>
  api.post(`/plants/${plantId}/daily-record`, data).then(unwrap);

export const getDailyRecords = (plantId: number, limit: number = 30): Promise<{ count: number; records: any[] }> =>
  api.get(`/plants/${plantId}/daily-records`, { params: { limit } }).then(unwrap);

export const deleteDailyRecord = (plantId: number, recordDate: string): Promise<{ success: boolean; message: string; deleted_count: number }> =>
  api.delete(`/plants/${plantId}/daily-records/${recordDate}`).then(unwrap);

// ─── Branding & Company Logo ────────────────────────────────────────────────
export const uploadCompanyLogo = (
  plantId: number,
  file: File,
): Promise<{ success: boolean; message: string; logo_url: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  return api
    .post(`/plants/${plantId}/logo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then(unwrap);
};

export const getCompanyLogoUrl = (plantId: number): string =>
  `/api/plants/${plantId}/logo`;

// ─── Settings & Maintenance ────────────────────────────────────────────────
export interface SystemStats {
  database_path?: string;
  db_size_bytes?: number;
  db_size_mb?: number;
  database_size_kb?: number;
  total_plants?: number;
  total_records?: number;
  total_daily_records?: number;
  total_reports?: number;
  reports_dir?: string;
  reports_folder?: string;
  reports_dir_size_mb?: number;
  reports_folder_size_kb?: number;
}

export const getSettings = (): Promise<{ settings: Record<string, string> }> =>
  api.get('/settings').then(unwrap);

export const updateSettings = (settings: Record<string, string>): Promise<{ success: boolean; message: string }> =>
  api.post('/settings', { settings }).then(unwrap);

export const getSystemStats = (): Promise<SystemStats> =>
  api.get('/settings/stats').then(unwrap);

export const getDatabaseBackupUrl = (): string =>
  `${(import.meta as any).env?.DEV ? 'http://localhost:8000/api' : '/api'}/settings/backup`;

export const optimizeDatabase = (): Promise<{ success: boolean; message: string; db_size_mb?: number }> =>
  api.post('/settings/optimize-db').then(unwrap);

export const clearSystemCache = (): Promise<{ success: boolean; message: string; files_cleared?: number }> =>
  api.post('/settings/clear-cache').then(unwrap);

export default api;

