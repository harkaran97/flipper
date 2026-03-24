/**
 * Detail screen hero section.
 * Car logo, make/model/year, asking price, 48px profit hero with spring entrance,
 * margin/effort caption, and opportunity class badge.
 * Profit is green (#34C759) for positive, red (#FF3B30) for negative.
 */
import React, { useEffect, useRef } from 'react'
import { View, Text, StyleSheet, Animated } from 'react-native'
import { OpportunityDetail } from '../lib/types'
import { formatPrice, formatDays } from '../lib/formatters'
import { CarLogo } from './CarLogo'
import { colours } from '../constants/colours'

interface Props {
  opportunity: OpportunityDetail
}

// Class badge — amber pill for SPECULATIVE, solid for others
function ClassBadge({ cls, writeOff }: { cls: string; writeOff: string }) {
  if (cls === 'exclude') return null

  const isSpeculative = cls === 'speculative'
  const bgMap: Record<string, string> = {
    strong: colours.green,
    worth_a_look: colours.worthALook,
  }

  if (isSpeculative) {
    return (
      <View style={styles.speculativePill}>
        <Text style={styles.speculativeText}>SPECULATIVE</Text>
      </View>
    )
  }

  const bg = bgMap[cls] ?? colours.textMuted
  return (
    <View style={[styles.classPill, { backgroundColor: bg }]}>
      <Text style={styles.classPillText}>
        {cls === 'strong' ? 'STRONG' : 'WORTH A LOOK'}
      </Text>
    </View>
  )
}

export const DetailHeader: React.FC<Props> = ({ opportunity }) => {
  const {
    make, model, year, listing_price_pence, true_profit_pence,
    true_margin_pct, total_man_days, opportunity_class,
    write_off_category, has_unpriced_faults,
  } = opportunity

  const isPositive = true_profit_pence >= 0
  const profitColour = isPositive ? colours.green : colours.riskHigh
  const profitText = isPositive
    ? `+${formatPrice(true_profit_pence)}`
    : `-${formatPrice(Math.abs(true_profit_pence))}`

  // Spring entrance animation: scale 0.8 → 1.0, opacity 0 → 1
  const scale = useRef(new Animated.Value(0.8)).current
  const opacity = useRef(new Animated.Value(0)).current

  useEffect(() => {
    Animated.parallel([
      Animated.spring(scale, { toValue: 1, useNativeDriver: true }),
      Animated.spring(opacity, { toValue: 1, useNativeDriver: true }),
    ]).start()
  }, [])

  const profitAnimStyle = {
    transform: [{ scale }],
    opacity,
  }

  const showWriteOff = write_off_category && write_off_category !== 'clean'

  return (
    <View style={styles.container}>
      {/* Car identity row */}
      <View style={styles.identityRow}>
        <CarLogo make={make} size={40} />
        <View style={styles.identityText}>
          <Text style={styles.carName} allowFontScaling={true}>
            {make} {model} {year ?? ''}
          </Text>
          <Text style={styles.askingPrice} allowFontScaling={true}>
            {formatPrice(listing_price_pence)} asking price
          </Text>
        </View>
      </View>

      {/* Profit hero */}
      <Text style={styles.profitLabel} allowFontScaling={false}>PROFIT</Text>
      <Animated.Text
        style={[styles.profitHero, { color: profitColour }, profitAnimStyle]}
        allowFontScaling={true}
        fontVariant={['tabular-nums']}
      >
        {profitText}
      </Animated.Text>
      <Text style={styles.profitCaption} allowFontScaling={true}>
        {true_margin_pct.toFixed(0)}% margin · {formatDays(total_man_days)} work
      </Text>

      {/* Badges */}
      <View style={styles.badgeRow}>
        <ClassBadge cls={opportunity_class} writeOff={write_off_category} />
        {showWriteOff && (
          <View style={[
            styles.classPill,
            { backgroundColor: write_off_category === 'Cat S' ? colours.catS : colours.catN },
          ]}>
            <Text style={styles.classPillText}>{write_off_category}</Text>
          </View>
        )}
      </View>

      {/* Unpriced warning */}
      {has_unpriced_faults && (
        <View style={styles.warningBanner}>
          <Text style={styles.warningText} allowFontScaling={true}>
            Profit is a floor estimate — some faults could not be priced.
          </Text>
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
  },
  identityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
  },
  identityText: { flex: 1 },
  carName: {
    fontSize: 18,
    fontWeight: '700',
    color: colours.textPrimary,
  },
  askingPrice: {
    fontSize: 14,
    fontWeight: '400',
    color: colours.textSecondary,
    marginTop: 2,
    fontVariant: ['tabular-nums'],
  },
  profitLabel: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.5,
    color: colours.textMuted,
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  profitHero: {
    fontSize: 48,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
    letterSpacing: -1,
  },
  profitCaption: {
    fontSize: 15,
    color: colours.textSecondary,
    marginTop: 4,
    fontVariant: ['tabular-nums'],
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
    marginTop: 16,
  },
  classPill: {
    borderRadius: 100,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  classPillText: {
    fontSize: 12,
    fontWeight: '600',
    color: colours.white,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
  },
  speculativePill: {
    borderRadius: 100,
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: 'rgba(255,149,0,0.15)',
  },
  speculativeText: {
    fontSize: 12,
    fontWeight: '600',
    color: colours.amber,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
  },
  warningBanner: {
    marginTop: 16,
    backgroundColor: colours.bg,
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: colours.border,
    borderLeftWidth: 3,
    borderLeftColor: colours.riskMedium,
  },
  warningText: {
    fontSize: 13,
    color: colours.textSecondary,
  },
})
