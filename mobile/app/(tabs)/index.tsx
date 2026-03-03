/**
 * Opportunities tab — the main feed screen.
 * Shows ranked opportunity cards with a filter bar.
 * Pull-to-refresh triggers a backend ingestion cycle.
 */
import React, { useState, useMemo } from 'react'
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

export default function OpportunitiesScreen() {
  const { data = [], isLoading } = useOpportunities()
  const { triggerRefresh, isRefreshing } = useRefresh()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<FilterValue>('all')

  const filtered = useMemo(() => {
    if (filter === 'all') return data.filter(o => o.opportunity_class !== 'exclude')
    return data.filter(o => o.opportunity_class === filter)
  }, [data, filter])

  const handleRefresh = async () => {
    await triggerRefresh()
    queryClient.invalidateQueries({ queryKey: ['opportunities'] })
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title} allowFontScaling={false}>Flipper</Text>
        <TouchableOpacity activeOpacity={0.7}>
          <Ionicons name="notifications-outline" size={24} color={colours.black} />
        </TouchableOpacity>
      </View>

      <FilterBar selected={filter} onSelect={setFilter} />

      <FlatList
        data={filtered}
        keyExtractor={item => item.id}
        renderItem={({ item }) => <OpportunityCard opportunity={item} />}
        contentContainerStyle={filtered.length === 0 ? styles.emptyContainer : styles.list}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing || isLoading}
            onRefresh={handleRefresh}
            tintColor={colours.green}
          />
        }
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState variant="feed" subtitle="Scanning eBay now." />
          ) : null
        }
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
    fontSize: 26,
    fontWeight: '700',
    letterSpacing: -0.5,
    color: colours.black,
  },
  list: {
    paddingTop: 8,
    paddingBottom: 24,
  },
  emptyContainer: {
    flexGrow: 1,
  },
})
