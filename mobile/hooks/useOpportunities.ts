/**
 * Fetches the ranked opportunities feed from the backend.
 * Merges saved/build status from AsyncStorage into each result.
 * Background refetch every 60 seconds.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { OpportunityCard } from '../lib/types'
import { getSavedIds, getBuildStatuses } from '../lib/storage'

const fetchOpportunities = async (): Promise<OpportunityCard[]> => {
  const [response, savedIds, buildStatuses] = await Promise.all([
    // Backend returns OpportunityFeedResponse: { opportunities, total, has_more }
    // Base URL: API_BASE_URL (constants/config.ts) → defaults to Railway deployment /api/v1
    // Full endpoint: <API_BASE_URL>/opportunities
    api.get<{ opportunities: OpportunityCard[]; total: number; has_more: boolean }>('/opportunities'),
    getSavedIds(),
    getBuildStatuses(),
  ])

  // DEBUG: log the raw API response so we can see what the app actually receives
  console.log('[useOpportunities] raw response status:', response.status)
  console.log('[useOpportunities] raw response data:', JSON.stringify(response.data, null, 2))
  console.log('[useOpportunities] opportunities array length:', response.data?.opportunities?.length ?? 'undefined — key missing or wrong shape')

  return response.data.opportunities.map(opp => ({
    ...opp,
    saved: savedIds.includes(opp.id),
    status: buildStatuses[opp.id] === 'active_build'
      ? 'active_build'
      : savedIds.includes(opp.id)
        ? 'saved'
        : 'new',
  }))
}

export const useOpportunities = () => {
  console.log('useOpportunities hook running')
  return useQuery({
    queryKey: ['opportunities'],
    queryFn: fetchOpportunities,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
}
