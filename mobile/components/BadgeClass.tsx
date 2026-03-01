/**
 * Coloured pill badge showing the opportunity classification:
 * STRONG, SPECULATIVE, WORTH A LOOK.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { OpportunityClass } from '../lib/types'
import { colours } from '../constants/colours'

const LABELS: Record<OpportunityClass, string> = {
  strong: 'STRONG',
  speculative: 'SPECULATIVE',
  worth_a_look: 'WORTH A LOOK',
  exclude: 'EXCLUDE',
}

const BG: Record<OpportunityClass, string> = {
  strong: colours.green,
  speculative: colours.speculative,
  worth_a_look: colours.worthALook,
  exclude: colours.exclude,
}

interface Props {
  opportunityClass: OpportunityClass
}

export const BadgeClass: React.FC<Props> = ({ opportunityClass }) => {
  if (opportunityClass === 'exclude') return null
  return (
    <View style={[styles.pill, { backgroundColor: BG[opportunityClass] }]}>
      <Text style={styles.label} allowFontScaling={true}>{LABELS[opportunityClass]}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  pill: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  label: {
    fontSize: 11,
    fontWeight: '600',
    color: colours.white,
    letterSpacing: 0.3,
  },
})
