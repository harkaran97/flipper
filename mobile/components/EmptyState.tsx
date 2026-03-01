/**
 * Full-screen empty state shown when a list has no items.
 * Displays a large emoji, heading, and subtext.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { colours } from '../constants/colours'

interface Props {
  emoji: string
  title: string
  subtitle: string
}

export const EmptyState: React.FC<Props> = ({ emoji, title, subtitle }) => (
  <View style={styles.container}>
    <Text style={styles.emoji} allowFontScaling={false}>{emoji}</Text>
    <Text style={styles.title} allowFontScaling={true}>{title}</Text>
    <Text style={styles.subtitle} allowFontScaling={true}>{subtitle}</Text>
  </View>
)

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingBottom: 80,
  },
  emoji: {
    fontSize: 48,
    marginBottom: 16,
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
