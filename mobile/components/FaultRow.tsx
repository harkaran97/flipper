/**
 * Single fault row shown in the detail screen faults section.
 * Uses View-based severity dots instead of emoji for precise colour control.
 * Dot types: filled circle = critical, half-filled = high, outline = medium/low.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { FaultDetail } from '../lib/types'
import { formatFaultType, formatDays } from '../lib/formatters'
import { colours } from '../constants/colours'

const DOT_SIZE = 10

function SeverityDot({ severity }: { severity: string }) {
  if (severity === 'critical') {
    return (
      <View style={[styles.dotBase, { backgroundColor: colours.riskHigh }]} />
    )
  }
  if (severity === 'high') {
    // Half-filled amber: outer circle with left half filled
    return (
      <View style={[styles.dotBase, { borderWidth: 1.5, borderColor: colours.amber, overflow: 'hidden' }]}>
        <View style={{ width: DOT_SIZE / 2, height: DOT_SIZE, backgroundColor: colours.amber }} />
      </View>
    )
  }
  // medium / low — outline grey
  const borderColor = severity === 'medium' ? 'rgba(60,60,67,0.4)' : colours.textMuted
  return (
    <View style={[styles.dotBase, { borderWidth: 1.5, borderColor }]} />
  )
}

interface Props {
  fault: FaultDetail
}

export const FaultRow: React.FC<Props> = ({ fault }) => {
  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <SeverityDot severity={fault.severity} />
        <Text style={styles.name} allowFontScaling={true} numberOfLines={1}>
          {formatFaultType(fault.fault_type)}
        </Text>
        <Text style={styles.days} allowFontScaling={true}>{formatDays(fault.labour_days)}</Text>
      </View>
      {fault.description ? (
        <Text style={styles.description} allowFontScaling={true} numberOfLines={1}>
          {fault.severity.charAt(0).toUpperCase() + fault.severity.slice(1)} — {fault.description}
        </Text>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: 'rgba(60,60,67,0.13)',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  dotBase: {
    width: DOT_SIZE,
    height: DOT_SIZE,
    borderRadius: DOT_SIZE / 2,
  },
  name: {
    flex: 1,
    fontSize: 17,
    fontWeight: '600',
    color: colours.textPrimary,
  },
  days: {
    fontSize: 15,
    color: colours.textSecondary,
    fontVariant: ['tabular-nums'],
  },
  description: {
    marginTop: 3,
    marginLeft: DOT_SIZE + 10,
    fontSize: 13,
    color: colours.textMuted,
  },
})
