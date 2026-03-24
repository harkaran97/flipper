/**
 * Opportunities tab — the main feed screen.
 * Shows ranked opportunity cards with a filter bar.
 * Pull-to-refresh triggers a backend ingestion cycle.
 */
import React, { useState, useMemo, useCallback } from 'react'
import {
  View, Text, FlatList, StyleSheet, TouchableOpacity,
  RefreshControl, SafeAreaView,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useOpportunities } from '../../hooks/useOpportunities'
import { useRefresh } from '../../hooks/useRefresh'
import { OpportunityCard } from '../../components/OpportunityCard'
import { FilterBar, FilterValue } from '../../components/FilterBar'
import { EmptyState } from '../../components/EmptyState'
import { colours } from '../../constants/colours'
import { useQueryClient } from '@tanstack/react-query'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { saveOpportunity } from '../../lib/api'
import { OpportunityCard as Opp } from '../../lib/types'

function FeedHero({ opportunityCount, topProfit }: { opportunityCount: number; topProfit: number | null }) {
  return (
    <View style={heroStyles.container}>
      {/* Top row: label + live indicator */}
      <View style={heroStyles.topRow}>
        <Text style={heroStyles.label}>Today's Opportunities</Text>
        <View style={heroStyles.liveRow}>
          <View style={heroStyles.liveDot} />
          <Text style={heroStyles.liveText}>Live</Text>
        </View>
      </View>

      {/* Big number */}
      <Text style={heroStyles.count}>{opportunityCount}</Text>
      <Text style={heroStyles.subtitle}>
        deals found · best profit{' '}
        <Text style={heroStyles.profit}>
          +£{topProfit != null ? topProfit.toLocaleString() : '—'}
        </Text>
      </Text>
    </View>
  )
}

const heroStyles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 16,
    borderRadius: 20,
    overflow: 'hidden',
    backgroundColor: '#F2F2F7',
    borderWidth: 0.5,
    borderColor: 'rgba(60,60,67,0.12)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    padding: 20,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(60,60,67,0.50)',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  liveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#34C759',
  },
  liveText: {
    fontSize: 11,
    color: '#34C759',
    fontWeight: '600',
  },
  count: {
    fontSize: 42,
    fontWeight: '700',
    letterSpacing: -1.5,
    color: '#000000',
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(60,60,67,0.55)',
    marginTop: 2,
  },
  profit: {
    color: '#34C759',
    fontWeight: '600',
  },
})

export default function OpportunitiesScreen() {
  console.log('OpportunitiesScreen mounted')
  const { data = [], isLoading, error } = useOpportunities()
  const { triggerRefresh, isRefreshing } = useRefresh()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<FilterValue>('all')
  const insets = useSafeAreaInsets()

  const filtered = useMemo(() => {
    if (filter === 'all') return data.filter(o => o.opportunity_class !== 'exclude')
    return data.filter(o => o.opportunity_class === filter)
  }, [data, filter])

  const opportunityCount = useMemo(
    () => data.filter(o => o.opportunity_class !== 'exclude').length,
    [data]
  )

  const topProfit = useMemo(() => {
    const profits = data.map(o => o.true_profit_pence / 100)
    return profits.length > 0 ? Math.max(...profits) : null
  }, [data])

  const handleRefresh = async () => {
    await triggerRefresh()
    queryClient.invalidateQueries({ queryKey: ['opportunities'] })
  }

  const handleSave = useCallback(async (id: string) => {
    // Optimistic update: mark as saved immediately
    queryClient.setQueryData(['opportunities'], (old: Opp[] | undefined) =>
      (old ?? []).map(o => o.id === id ? { ...o, saved: true } : o)
    )
    await saveOpportunity(id)
    // Refresh saved tab
    queryClient.invalidateQueries({ queryKey: ['opportunities', 'saved'] })
  }, [queryClient])

  const handleDismiss = useCallback((id: string) => {
    // Optimistic update: remove from feed immediately
    queryClient.setQueryData(['opportunities'], (old: Opp[] | undefined) =>
      (old ?? []).filter(o => o.id !== id)
    )
  }, [queryClient])

  const emptyComponent = useMemo(() => {
    if (isLoading) return null
    if (data.length === 0) {
      return (
        <EmptyState
          icon="📡"
          title="No opportunities yet"
          subtitle={error ? 'Could not load — pull down to retry.' : 'The next scan runs at 9AM. Pull down to check for new listings.'}
        />
      )
    }
    if (filtered.length === 0) {
      const filterLabel = filter === 'all' ? 'ALL' : filter.replace('_', ' ').toUpperCase()
      return (
        <EmptyState
          icon="🔍"
          title={`No ${filterLabel} deals right now`}
          subtitle="Check back after 9AM when the daily scan runs, or try a different filter."
        />
      )
    }
    return null
  }, [isLoading, data.length, filtered.length, filter, error])

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title} allowFontScaling={false}>Flipper</Text>
          <Text style={styles.subtitle} allowFontScaling={false}>UK car flipping, simplified</Text>
        </View>
        <TouchableOpacity activeOpacity={0.7}>
          <Ionicons name="notifications-outline" size={24} color={colours.black} />
        </TouchableOpacity>
      </View>

      {/* Hero — above filters, always shows total count across ALL opps */}
      <FeedHero opportunityCount={opportunityCount} topProfit={topProfit} />

      <FilterBar selected={filter} onSelect={setFilter} />

      <FlatList
        data={filtered}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <OpportunityCard
            opportunity={item}
            onSave={handleSave}
            onDismiss={handleDismiss}
          />
        )}
        contentContainerStyle={[
          filtered.length === 0 ? styles.emptyContainer : styles.list,
          { paddingBottom: insets.bottom + 90 },
        ]}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing || isLoading}
            onRefresh={handleRefresh}
            tintColor={colours.green}
          />
        }
        ListEmptyComponent={emptyComponent}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colours.bg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
    backgroundColor: colours.bg,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    letterSpacing: -0.5,
    color: colours.black,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(60,60,67,0.50)',
    marginTop: 2,
  },
  list: {
    paddingTop: 8,
  },
  emptyContainer: {
    flexGrow: 1,
  },
})
