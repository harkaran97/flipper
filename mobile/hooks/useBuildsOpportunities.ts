/**
 * Fetches opportunities marked as active builds from the backend.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { OpportunityCard } from '../lib/types'

const fetchBuilds = async (): Promise<OpportunityCard[]> => {
  const response = await api.get('/opportunities/builds')
  return response.data.opportunities ?? []
}

export const useBuildsOpportunities = () => {
  return useQuery({
    queryKey: ['opportunities', 'builds'],
    queryFn: fetchBuilds,
  })
}
