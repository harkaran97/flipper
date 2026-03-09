/**
 * My Builds tab — shows opportunities marked as active builds.
 * Promoted from detail screen via "Mark as Build" button.
 */
import React, { useMemo } from 'react'
import { FlatList, StyleSheet, SafeAreaView, View, Text } from 'react-native'
import { useOpportunities } from '../../hooks/useOpportunities'
import { OpportunityCard } from '../../components/OpportunityCard'
import { EmptyState } from '../../components/EmptyState'
import { colours } from '../../constants/colours'

export default function BuildsScreen() {
  const { data = [], isLoading } = useOpportunities()
  const builds = useMemo(() => data.filter(o => o.status === 'active_build'), [data])

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title} allowFontScaling={false}>My Builds</Text>
      </View>

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
  header: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
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
