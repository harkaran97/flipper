/**
 * Opportunity card shown in the feed list.
 * Displays car name, asking price, profit, days, faults summary, and badges.
 * Swipe right → save (green bookmark). Swipe left → dismiss (red X).
 */
import React, { useRef } from 'react'
import {
  View, Text, StyleSheet, TouchableOpacity, Animated,
} from 'react-native'
import { Swipeable } from 'react-native-gesture-handler'
import { router } from 'expo-router'
import { OpportunityCard as Opp } from '../lib/types'
import { formatPrice, formatProfit, formatDays } from '../lib/formatters'
import { CarLogo } from './CarLogo'
import { BadgeClass } from './BadgeClass'
import { BadgeRisk } from './BadgeRisk'
import { colours } from '../constants/colours'

interface Props {
  opportunity: Opp
  onSave?: (id: string) => void
  onDismiss?: (id: string) => void
}

export const OpportunityCard: React.FC<Props> = ({ opportunity, onSave, onDismiss }) => {
  const {
    id, make, model, year, listing_price_pence, true_profit_pence,
    total_man_days, opportunity_class, risk_level, write_off_category,
    detected_faults_summary,
  } = opportunity

  const swipeableRef = useRef<Swipeable>(null)
  const showWriteOff = write_off_category && write_off_category !== 'clean'

  const renderLeftActions = (_progress: Animated.AnimatedInterpolation<number>, dragX: Animated.AnimatedInterpolation<number>) => {
    if (!onSave) return null
    const opacity = dragX.interpolate({
      inputRange: [40, 80],
      outputRange: [0, 1],
      extrapolate: 'clamp',
    })
    const scale = dragX.interpolate({
      inputRange: [40, 80],
      outputRange: [0.8, 1],
      extrapolate: 'clamp',
    })
    return (
      <Animated.View style={[styles.actionContainer, { opacity, transform: [{ scale }] }]}>
        <View style={[styles.actionCircle, { backgroundColor: '#34C759' }]}>
          <Text style={styles.actionIcon}>🔖</Text>
        </View>
      </Animated.View>
    )
  }

  const renderRightActions = (_progress: Animated.AnimatedInterpolation<number>, dragX: Animated.AnimatedInterpolation<number>) => {
    if (!onDismiss) return null
    const opacity = dragX.interpolate({
      inputRange: [-80, -40],
      outputRange: [1, 0],
      extrapolate: 'clamp',
    })
    const scale = dragX.interpolate({
      inputRange: [-80, -40],
      outputRange: [1, 0.8],
      extrapolate: 'clamp',
    })
    return (
      <Animated.View style={[styles.actionContainer, { opacity, transform: [{ scale }] }]}>
        <View style={[styles.actionCircle, { backgroundColor: '#FF3B30' }]}>
          <Text style={styles.actionIconDismiss}>✕</Text>
        </View>
      </Animated.View>
    )
  }

  const handleSwipeOpen = (direction: 'left' | 'right') => {
    if (direction === 'left' && onSave) {
      onSave(id)
      swipeableRef.current?.close()
    } else if (direction === 'right' && onDismiss) {
      onDismiss(id)
      swipeableRef.current?.close()
    }
  }

  return (
    <View style={styles.wrapper}>
      <Swipeable
        ref={swipeableRef}
        renderLeftActions={renderLeftActions}
        renderRightActions={renderRightActions}
        onSwipeableOpen={handleSwipeOpen}
        leftThreshold={60}
        rightThreshold={60}
        friction={2}
        overshootLeft={false}
        overshootRight={false}
      >
        <TouchableOpacity
          style={styles.card}
          onPress={() => router.push(`/opportunity/${id}`)}
          activeOpacity={0.95}
        >
          {/* Row 1: Logo + Car name + Class badge */}
          <View style={styles.topRow}>
            <CarLogo make={make} size={40} />
            <Text style={styles.carName} numberOfLines={1} allowFontScaling={true}>
              {(() => {
                const displayYear = year && year > 1900 ? ` ${year}` : ''
                const displayModel = model.toLowerCase().startsWith(make.toLowerCase())
                  ? model
                  : `${make} ${model}`
                return `${displayModel}${displayYear}`
              })()}
            </Text>
            <BadgeClass opportunityClass={opportunity_class} />
          </View>

          {/* Row 2: 3-column metrics with UPPERCASE labels */}
          <View style={styles.metricsRow}>
            <View style={styles.metricCol}>
              <Text style={styles.metricLabel} allowFontScaling={false}>PROFIT</Text>
              <Text style={styles.profit} allowFontScaling={true}>
                {formatProfit(true_profit_pence)}
              </Text>
            </View>
            <View style={styles.metricCol}>
              <Text style={styles.metricLabel} allowFontScaling={false}>ASKING</Text>
              <Text style={styles.askingPrice} allowFontScaling={true}>
                {formatPrice(listing_price_pence)}
              </Text>
            </View>
            <View style={styles.metricCol}>
              <Text style={styles.metricLabel} allowFontScaling={false}>DAYS</Text>
              <Text style={styles.days} allowFontScaling={true}>
                {formatDays(total_man_days)}
              </Text>
            </View>
          </View>

          {/* Row 3: Fault summary + badges */}
          <View style={styles.bottomRow}>
            <Text style={styles.faultSummary} numberOfLines={1} allowFontScaling={true}>
              {detected_faults_summary ?? '—'}
            </Text>
            <View style={styles.badges}>
              {showWriteOff && (
                <View style={[styles.writeOffBadge, {
                  backgroundColor: write_off_category === 'Cat S' ? colours.catS : colours.catN
                }]}>
                  <Text style={styles.writeOffText} allowFontScaling={false}>
                    {write_off_category}
                  </Text>
                </View>
              )}
              <BadgeRisk risk={risk_level} />
            </View>
          </View>
        </TouchableOpacity>
      </Swipeable>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 8,
    overflow: 'hidden',
  },
  actionContainer: {
    width: 80,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionIcon: {
    fontSize: 20,
  },
  actionIconDismiss: {
    color: '#FFF',
    fontSize: 20,
    fontWeight: '700',
  },
  card: {
    backgroundColor: colours.bgCard,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colours.border,
    padding: 16,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 16,
  },
  carName: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: colours.textPrimary,
  },
  metricsRow: {
    flexDirection: 'row',
    marginBottom: 16,
    gap: 24,
  },
  metricCol: {
    flexDirection: 'column',
  },
  metricLabel: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.8,
    color: colours.textMuted,
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  profit: {
    fontSize: 20,
    fontWeight: '700',
    color: colours.green,
    fontVariant: ['tabular-nums'],
  },
  askingPrice: {
    fontSize: 14,
    fontWeight: '500',
    color: colours.textSecondary,
    fontVariant: ['tabular-nums'],
  },
  days: {
    fontSize: 14,
    fontWeight: '500',
    color: colours.textSecondary,
    fontVariant: ['tabular-nums'],
  },
  bottomRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  faultSummary: {
    flex: 1,
    fontSize: 13,
    color: colours.textSecondary,
  },
  badges: {
    flexDirection: 'row',
    gap: 6,
  },
  writeOffBadge: {
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  writeOffText: {
    fontSize: 11,
    fontWeight: '600',
    color: colours.white,
  },
})
