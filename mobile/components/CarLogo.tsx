/**
 * Circular car manufacturer logo badge.
 * Falls back gracefully to a grey initials circle if logo URL is not found.
 * Never crashes — always renders something.
 */
import React, { useState } from 'react'
import { View, Image, Text, StyleSheet } from 'react-native'
import { getCarLogoUrl } from '../lib/logos'
import { colours } from '../constants/colours'

interface Props {
  make: string
  size?: number
}

export const CarLogo: React.FC<Props> = ({ make, size = 40 }) => {
  const url = getCarLogoUrl(make)
  const [errored, setErrored] = useState(false)

  const initials = make.slice(0, 2).toUpperCase()

  if (!url || errored) {
    return (
      <View style={[styles.fallback, { width: size, height: size, borderRadius: size / 2 }]}>
        <Text style={styles.initials} allowFontScaling={false}>{initials}</Text>
      </View>
    )
  }

  return (
    <Image
      source={{ uri: url }}
      style={{ width: size, height: size, borderRadius: size / 2 }}
      resizeMode="contain"
      onError={() => setErrored(true)}
    />
  )
}

const styles = StyleSheet.create({
  fallback: {
    backgroundColor: colours.bgSecondary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  initials: {
    fontSize: 13,
    fontWeight: '600',
    color: colours.textSecondary,
  },
})
