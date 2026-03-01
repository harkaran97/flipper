/**
 * 24x24 supplier favicon shown inline with supplier name and price.
 * Falls back to a grey square if favicon fails to load.
 */
import React, { useState } from 'react'
import { View, Image, StyleSheet } from 'react-native'
import { getSupplierLogo } from '../lib/supplierLogos'
import { colours } from '../constants/colours'

interface Props {
  supplier: string
  size?: number
}

export const SupplierLogo: React.FC<Props> = ({ supplier, size = 24 }) => {
  const url = getSupplierLogo(supplier)
  const [errored, setErrored] = useState(false)

  if (!url || errored) {
    return <View style={[styles.fallback, { width: size, height: size }]} />
  }

  return (
    <Image
      source={{ uri: url }}
      style={{ width: size, height: size, borderRadius: 4 }}
      resizeMode="contain"
      onError={() => setErrored(true)}
    />
  )
}

const styles = StyleSheet.create({
  fallback: {
    backgroundColor: colours.border,
    borderRadius: 4,
  },
})
