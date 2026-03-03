/**
 * My Builds tab — shows opportunities marked as active builds.
 * Promoted from detail screen via "Mark as Build" button.
 */
import React, { useMemo } from 'react'
import { FlatList, StyleSheet, SafeAreaView } from 'react-native'
import { useOpportunities } from '../../hooks/useOpportunities'
import { OpportunityCard } from '../../components/OpportunityCard'
import { EmptyState } from '../../components/EmptyState'
import { colours } from '../../constants/colours'

export default function BuildsScreen() {
  const { data = [], isLoading } = useOpportunities()
  const builds = useMemo(() => data.filter(o => o.status === 'active_build'), [data])

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={builds}
        keyExtractor={item => item.id}
        renderItem={({ item }) => <OpportunityCard opportunity={item} />}
        contentContainerStyle={builds.length === 0 ? styles.emptyContainer : styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              title="No active builds."
              subtitle="Mark an opportunity as a build to track it here."
            />
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
  list: {
    paddingTop: 8,
    paddingBottom: 24,
  },
  emptyContainer: {
    flexGrow: 1,
  },
})
