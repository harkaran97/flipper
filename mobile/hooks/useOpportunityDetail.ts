/**
 * Fetches full opportunity detail including faults and parts breakdown.
 * saved and marked_as_build come from the backend response.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { OpportunityDetail } from '../lib/types'

const fetchDetail = async (id: string): Promise<OpportunityDetail> => {
  const response = await api.get<OpportunityDetail>(`/opportunities/${id}`)
  return response.data
}

export const useOpportunityDetail = (id: string) => {
  return useQuery({
    queryKey: ['opportunity', id],
    queryFn: () => fetchDetail(id),
    enabled: !!id,
    staleTime: 60_000,
  })
}
