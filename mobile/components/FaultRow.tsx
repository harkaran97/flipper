/**
 * Single fault row shown in the detail screen faults section.
 * Colour-codes severity with an emoji indicator and shows labour days.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { FaultDetail } from '../lib/types'
import { formatFaultType, formatDays } from '../lib/formatters'
import { colours } from '../constants/colours'

const SEVERITY_ICON: Record<string, string> = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '⚪',
}

interface Props {
  fault: FaultDetail
}

export const FaultRow: React.FC<Props> = ({ fault }) => {
  const icon = SEVERITY_ICON[fault.severity] ?? '⚪'
  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <Text style={styles.icon} allowFontScaling={false}>{icon}</Text>
        <Text style={styles.name} allowFontScaling={true}>{formatFaultType(fault.fault_type)}</Text>
        <Text style={styles.days} allowFontScaling={true}>{formatDays(fault.labour_days)}</Text>
      </View>
      {fault.description ? (
        <Text style={styles.description} allowFontScaling={true}>
          {fault.severity.charAt(0).toUpperCase() + fault.severity.slice(1)} — {fault.description}
        </Text>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colours.border,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    fontSize: 16,
    marginRight: 8,
  },
  name: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: colours.textPrimary,
  },
  days: {
    fontSize: 14,
    color: colours.textSecondary,
  },
  description: {
    marginTop: 4,
    marginLeft: 24,
    fontSize: 13,
    color: colours.textSecondary,
  },
})
