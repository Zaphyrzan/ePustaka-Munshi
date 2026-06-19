import axios from 'axios'

// Flask API base. Dev: local Flask on :5000. Prod: same origin (empty string),
// since the React app and the Flask API share one Vercel deployment.
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'
const baseURL = API_BASE

export const api = axios.create({
  baseURL,
  withCredentials: true, // Flask-Login session cookie
  headers: { 'Content-Type': 'application/json' },
})

// Every endpoint wraps payloads as { success, message, data }
export interface ApiEnvelope<T> {
  success: boolean
  message?: string
  data: T
}

export interface Pagination {
  page: number
  per_page: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface Paginated<T> {
  items: T[]
  pagination: Pagination
}

/** Unwrap the API envelope, throwing the server's message on failure */
export async function unwrap<T>(promise: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  try {
    const res = await promise
    if (!res.data.success) throw new Error(res.data.message || 'Request failed')
    return res.data.data
  } catch (err) {
    if (axios.isAxiosError<ApiEnvelope<unknown>>(err)) {
      const message = err.response?.data?.message
      if (message) throw new Error(message)
    }
    throw err
  }
}
