import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { OpportunityCard } from '../lib/types'

const fetchOpportunities = async (): Promise<OpportunityCard[]> => {
  console.log('fetchOpportunities called')
  const response = await api.get('/opportunities')
  console.log('response:', JSON.stringify(response.data))
  return response.data.opportunities ?? []
}

export const useOpportunities = () => {
  console.log('useOpportunities called')
  return useQuery({
    queryKey: ['opportunities'],
    queryFn: fetchOpportunities,
  })
}
