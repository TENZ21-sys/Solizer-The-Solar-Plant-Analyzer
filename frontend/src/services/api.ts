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

// ─── Daily Manual Entry ─────────────────────────────────────────────────────
export const addDailyRecord = (
  plantId: number,
  data: DailyRecordInput,
): Promise<DailyRecordInputResponse> =>
  api.post(`/plants/${plantId}/daily-record`, data).then(unwrap);

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

export default api;

