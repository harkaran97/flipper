/**
 * Saved tab — shows opportunities the user has swiped right to save.
 * Data comes from the backend /opportunities/saved endpoint.
 */
import React from 'react'
import { View, Text, FlatList, StyleSheet } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useSavedOpportunities } from '../../hooks/useSavedOpportunities'
import { OpportunityCard } from '../../components/OpportunityCard'
import { EmptyState } from '../../components/EmptyState'
import { colours } from '../../constants/colours'

export default function SavedScreen() {
  const { data = [], isLoading } = useSavedOpportunities()
  const insets = useSafeAreaInsets()

  return (
    <View style={styles.container}>
      <FlatList
        data={data}
        keyExtractor={item => item.id}
        renderItem={({ item }) => <OpportunityCard opportunity={item} source="Saved" />}
        ListHeaderComponent={
          <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
            <Text style={styles.title}>Saved</Text>
          </View>
        }
        contentContainerStyle={[
          styles.listContent,
          { paddingBottom: insets.bottom + 88 },
        ]}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              icon="🔖"
              title="Nothing saved yet"
              subtitle="Swipe right on a deal to save it for later."
            />
          ) : null
        }
        showsVerticalScrollIndicator={false}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colours.bg,
  },
  header: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    letterSpacing: -0.5,
    color: colours.black,
  },
  listContent: {},
})
