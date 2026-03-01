/**
 * Returns the subset of opportunities that the user has saved locally.
 * Reuses useOpportunities and filters client-side.
 */
import { useMemo } from 'react'
import { useOpportunities } from './useOpportunities'

export const useSavedOpportunities = () => {
  const { data, ...rest } = useOpportunities()
  const saved = useMemo(
    () => (data ?? []).filter(opp => opp.saved === true),
    [data],
  )
  return { data: saved, ...rest }
}
