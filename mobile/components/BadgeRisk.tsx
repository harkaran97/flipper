/**
 * Risk level pill badge — hidden for low risk, amber for medium, red for high.
 * Shown on opportunity cards and detail header.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { RiskLevel } from '../lib/types'
import { colours } from '../constants/colours'

const CONFIG: Record<RiskLevel, { label: string; colour: string } | null> = {
  low: null,
  medium: { label: 'MED RISK', colour: colours.riskMedium },
  high: { label: 'HIGH RISK', colour: colours.danger },
}

interface Props {
  risk: RiskLevel
}

export const BadgeRisk: React.FC<Props> = ({ risk }) => {
  const config = CONFIG[risk]
  if (!config) return null
  return (
    <View style={[styles.pill, { borderColor: config.colour }]}>
      <Text style={[styles.label, { color: config.colour }]} allowFontScaling={false}>
        {config.label}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  pill: {
    borderRadius: 4,
    borderWidth: 1,
    paddingHorizontal: 7,
    paddingVertical: 3,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
})
