/**
 * Saved tab — shows only opportunities the user has swiped to save.
 * Swipe left to remove from saved.
 */
import React from 'react'
import { FlatList, StyleSheet, SafeAreaView } from 'react-native'
import { useSavedOpportunities } from '../../hooks/useSavedOpportunities'
import { OpportunityCard } from '../../components/OpportunityCard'
import { EmptyState } from '../../components/EmptyState'
import { colours } from '../../constants/colours'

export default function SavedScreen() {
  const { data = [], isLoading } = useSavedOpportunities()

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
              title="Nothing saved."
              subtitle="Swipe left on any opportunity to save it."
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
