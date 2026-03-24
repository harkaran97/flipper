/**
 * Fetches saved opportunities from the backend.
 * Uses a dedicated query key so the Saved tab refreshes independently.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { OpportunityCard } from '../lib/types'

const fetchSaved = async (): Promise<OpportunityCard[]> => {
  const response = await api.get('/opportunities/saved')
  return response.data.opportunities ?? []
}

export const useSavedOpportunities = () => {
  return useQuery({
    queryKey: ['opportunities', 'saved'],
    queryFn: fetchSaved,
  })
}
