/**
 * Horizontally scrolling filter pill bar for the opportunities feed.
 * Filters: All, Strong, Speculative, Worth a Look.
 * Single-select; filters the list client-side.
 */
import React from 'react'
import { ScrollView, TouchableOpacity, Text, StyleSheet, View } from 'react-native'
import { OpportunityClass } from '../lib/types'
import { colours } from '../constants/colours'

export type FilterValue = 'all' | OpportunityClass

const FILTERS: { label: string; value: FilterValue }[] = [
  { label: 'All', value: 'all' },
  { label: 'Strong', value: 'strong' },
  { label: 'Speculative', value: 'speculative' },
  { label: 'Worth a Look', value: 'worth_a_look' },
]

interface Props {
  selected: FilterValue
  onSelect: (value: FilterValue) => void
}

export const FilterBar: React.FC<Props> = ({ selected, onSelect }) => (
  <ScrollView
    horizontal
    showsHorizontalScrollIndicator={false}
    contentContainerStyle={styles.container}
  >
    {FILTERS.map(f => {
      const active = f.value === selected
      return (
        <TouchableOpacity
          key={f.value}
          style={[styles.pill, active && styles.pillActive]}
          onPress={() => onSelect(f.value)}
          activeOpacity={0.7}
        >
          <Text
            style={[styles.label, active && styles.labelActive]}
            allowFontScaling={true}
          >
            {f.label}
          </Text>
        </TouchableOpacity>
      )
    })}
    <View style={styles.trailing} />
  </ScrollView>
)

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 8,
    flexDirection: 'row',
  },
  pill: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colours.border,
    paddingHorizontal: 14,
    paddingVertical: 6,
    backgroundColor: colours.bg,
  },
  pillActive: {
    backgroundColor: colours.black,
    borderColor: colours.black,
  },
  label: {
    fontSize: 13,
    fontWeight: '500',
    color: colours.textSecondary,
  },
  labelActive: {
    color: colours.white,
    fontWeight: '600',
  },
  trailing: { width: 8 },
})
