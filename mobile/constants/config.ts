/** App-wide configuration. API_BASE_URL defaults to the live Railway deployment. */
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? 'https://flipper-production-dca0.up.railway.app/api/v1'
