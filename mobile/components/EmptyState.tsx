/**
 * Full-screen empty state shown when a list has no items.
 * Feed variant: large "0" hero + OPPORTUNITIES label + subtitle.
 * Default variant: title + subtitle, no emoji.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { colours } from '../constants/colours'

interface Props {
  variant?: 'feed' | 'default'
  title?: string
  subtitle?: string
}

export const EmptyState: React.FC<Props> = ({ variant = 'default', title, subtitle }) => {
  if (variant === 'feed') {
    return (
      <View style={styles.container}>
        <Text style={styles.bigNumber} allowFontScaling={false}>0</Text>
        <Text style={styles.bigNumberLabel} allowFontScaling={false}>OPPORTUNITIES</Text>
        {subtitle ? (
          <Text style={styles.feedSubtitle} allowFontScaling={false}>{subtitle}</Text>
        ) : null}
      </View>
    )
  }

  return (
    <View style={styles.container}>
      {title ? (
        <Text style={styles.title} allowFontScaling={true}>{title}</Text>
      ) : null}
      {subtitle ? (
        <Text style={styles.subtitle} allowFontScaling={true}>{subtitle}</Text>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingBottom: 80,
  },
  bigNumber: {
    fontSize: 64,
    fontWeight: '800',
    color: colours.green,
    fontVariant: ['tabular-nums'],
  },
  bigNumberLabel: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 1.2,
    color: colours.textMuted,
    textTransform: 'uppercase',
    marginTop: 4,
  },
  feedSubtitle: {
    fontSize: 13,
    color: colours.textMuted,
    marginTop: 8,
  },
  title: {
    fontSize: 17,
    fontWeight: '600',
    color: colours.textPrimary,
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    color: colours.textMuted,
    textAlign: 'center',
    lineHeight: 22,
  },
})
