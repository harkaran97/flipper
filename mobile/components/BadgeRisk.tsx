/**
 * Risk level pill badge — hidden for low risk, amber for medium, red for high.
 * Shown on opportunity cards and detail header.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { RiskLevel } from '../lib/types'
import { colours } from '../constants/colours'

const CONFIG: Record<RiskLevel, { icon: string; colour: string } | null> = {
  low: null,
  medium: { icon: '⚠', colour: colours.riskMedium },
  high: { icon: '🔴', colour: colours.riskHigh },
}

interface Props {
  risk: RiskLevel
}

export const BadgeRisk: React.FC<Props> = ({ risk }) => {
  const config = CONFIG[risk]
  if (!config) return null
  return (
    <View style={[styles.pill, { borderColor: config.colour }]}>
      <Text style={[styles.label, { color: config.colour }]} allowFontScaling={true}>
        {config.icon} {risk.charAt(0).toUpperCase() + risk.slice(1)}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  pill: {
    borderRadius: 6,
    borderWidth: 1,
    paddingHorizontal: 7,
    paddingVertical: 3,
  },
  label: {
    fontSize: 11,
    fontWeight: '600',
  },
})
