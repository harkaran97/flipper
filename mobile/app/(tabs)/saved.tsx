/**
 * Saved tab — shows opportunities the user has swiped right to save.
 * Data comes from the backend /opportunities/saved endpoint.
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
              icon="🔖"
              title="Nothing saved yet"
              subtitle="Swipe right on a deal to save it for later."
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
