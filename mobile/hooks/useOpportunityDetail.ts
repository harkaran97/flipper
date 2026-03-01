/**
 * Fetches full opportunity detail including faults and parts breakdown.
 * Merges saved/build status from AsyncStorage.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { OpportunityDetail } from '../lib/types'
import { getSavedIds, getBuildStatuses } from '../lib/storage'

const fetchDetail = async (id: string): Promise<OpportunityDetail> => {
  const [response, savedIds, buildStatuses] = await Promise.all([
    api.get<OpportunityDetail>(`/opportunities/${id}`),
    getSavedIds(),
    getBuildStatuses(),
  ])
  const opp = response.data
  return {
    ...opp,
    saved: savedIds.includes(opp.id),
    status: buildStatuses[opp.id] === 'active_build'
      ? 'active_build'
      : savedIds.includes(opp.id)
        ? 'saved'
        : 'new',
  }
}

export const useOpportunityDetail = (id: string) => {
  return useQuery({
    queryKey: ['opportunity', id],
    queryFn: () => fetchDetail(id),
    enabled: !!id,
    staleTime: 60_000,
  })
}
