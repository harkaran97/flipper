/** Axios HTTP client configured to talk to the Flipper backend API. */
import axios from 'axios'
import { API_BASE_URL } from '../constants/config'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

export const saveOpportunity = (id: string) =>
  api.post(`/opportunities/${id}/save`)

export const unsaveOpportunity = (id: string) =>
  api.post(`/opportunities/${id}/unsave`)

export const markAsBuildApi = (id: string) =>
  api.post(`/opportunities/${id}/mark-build`)

export const unmarkAsBuildApi = (id: string) =>
  api.post(`/opportunities/${id}/unmark-build`)
