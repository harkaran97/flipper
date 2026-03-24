/**
 * My Builds tab — shows opportunities marked as active builds.
 * Data comes from the backend /opportunities/builds endpoint.
 */
import React from 'react'
import { View, Text, FlatList, StyleSheet } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useBuildsOpportunities } from '../../hooks/useBuildsOpportunities'
import { OpportunityCard } from '../../components/OpportunityCard'
import { EmptyState } from '../../components/EmptyState'
import { colours } from '../../constants/colours'

export default function BuildsScreen() {
  const { data = [], isLoading } = useBuildsOpportunities()
  const insets = useSafeAreaInsets()

  return (
    <View style={styles.container}>
      <FlatList
        data={data}
        keyExtractor={item => item.id}
        renderItem={({ item }) => <OpportunityCard opportunity={item} source="Builds" />}
        ListHeaderComponent={
          <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
            <Text style={styles.title}>Builds</Text>
          </View>
        }
        contentContainerStyle={[
          styles.listContent,
          { paddingBottom: insets.bottom + 88 },
        ]}
        ListEmptyComponent={
          !isLoading ? (
            <EmptyState
              icon="🔧"
              title="No builds tracked"
              subtitle="Tap 'Mark as Build' on an opportunity to track your active projects here."
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
