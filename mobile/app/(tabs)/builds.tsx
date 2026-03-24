/**
 * My Builds tab — shows opportunities marked as active builds.
 * Data comes from the backend /opportunities/builds endpoint.
 */
import React from 'react'
import { FlatList, StyleSheet, SafeAreaView } from 'react-native'
import { useBuildsOpportunities } from '../../hooks/useBuildsOpportunities'
import { OpportunityCard } from '../../components/OpportunityCard'
import { EmptyState } from '../../components/EmptyState'
import { colours } from '../../constants/colours'

export default function BuildsScreen() {
  const { data = [], isLoading } = useBuildsOpportunities()

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={data}
        keyExtractor={item => item.id}
        renderItem={({ item }) => <OpportunityCard opportunity={item} />}
        contentContainerStyle={data.length === 0 ? styles.emptyContainer : styles.list}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              icon="🔧"
              title="No builds tracked"
              subtitle="Tap 'Mark as Build' on an opportunity to track your active projects here."
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
