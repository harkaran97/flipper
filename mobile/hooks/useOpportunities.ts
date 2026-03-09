import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { getSavedIds, getBuildStatuses } from '../lib/storage'
import { OpportunityCard } from '../lib/types'

const fetchOpportunities = async (): Promise<OpportunityCard[]> => {
  const [response, savedIds, buildStatuses] = await Promise.all([
    api.get('/opportunities'),
    getSavedIds(),
    getBuildStatuses(),
  ])
  const opportunities: OpportunityCard[] = response.data.opportunities ?? []
  const savedSet = new Set(savedIds)
  return opportunities.map(opp => ({
    ...opp,
    saved: savedSet.has(opp.id),
    status: buildStatuses[opp.id] === 'active_build' ? 'active_build' : (opp.status ?? 'new'),
  }))
}

export const useOpportunities = () => {
  return useQuery({
    queryKey: ['opportunities'],
    queryFn: fetchOpportunities,
  })
}
