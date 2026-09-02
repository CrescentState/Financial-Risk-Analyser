import axios, { AxiosError } from 'axios';
import type { PipelineResult } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ApiError {
  detail: string;
}

export const analyzeTicker = async (ticker: string): Promise<PipelineResult> => {
  try {
    const response = await api.post<PipelineResult>(`/analyze/${ticker.toUpperCase()}`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      if (axiosError.response?.status === 400) {
        throw new Error(`Invalid ticker: ${axiosError.response.data?.detail || 'Unknown error'}`);
      }
      if (axiosError.response?.status === 500) {
        throw new Error(`Pipeline error: ${axiosError.response.data?.detail || 'Unknown error'}`);
      }
      if (axiosError.code === 'ECONNABORTED') {
        throw new Error('Request timed out. The pipeline took too long.');
      }
      if (axiosError.code === 'ERR_NETWORK' || axiosError.code === 'ECONNREFUSED') {
        throw new Error('Cannot connect to API. Is the backend running?');
      }
      throw new Error(`API error: ${axiosError.message}`);
    }
    throw error;
  }
};

export const checkHealth = async (): Promise<boolean> => {
  try {
    const response = await api.get('/health', { timeout: 5000 });
    return response.status === 200;
  } catch {
    return false;
  }
};