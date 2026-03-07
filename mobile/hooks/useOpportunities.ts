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
    api.get<{ opportunities: OpportunityCard[]; total: number }>('/opportunities'),
    getSavedIds(),
    getBuildStatuses(),
  ])
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
  return useQuery({
    queryKey: ['opportunities'],
    queryFn: fetchOpportunities,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
}
