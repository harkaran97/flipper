/**
 * Opportunity card shown in the feed list.
 * Displays car name, asking price, profit, days, faults summary, and badges.
 * Supports swipe-left gesture to save/remove via a Touchable reveal.
 */
import React, { useRef, useState } from 'react'
import {
  View, Text, StyleSheet, TouchableOpacity,
  Animated, PanResponder, Dimensions,
} from 'react-native'
import { router } from 'expo-router'
import { OpportunityCard as Opp } from '../lib/types'
import { formatPrice, formatProfit, formatDays } from '../lib/formatters'
import { CarLogo } from './CarLogo'
import { BadgeClass } from './BadgeClass'
import { BadgeRisk } from './BadgeRisk'
import { colours } from '../constants/colours'
import { toggleSaved } from '../lib/storage'
import { useQueryClient } from '@tanstack/react-query'

const SWIPE_THRESHOLD = -80
const SCREEN_WIDTH = Dimensions.get('window').width

interface Props {
  opportunity: Opp
}

export const OpportunityCard: React.FC<Props> = ({ opportunity }) => {
  const {
    id, make, model, year, listing_price_pence, true_profit_pence,
    total_man_days, opportunity_class, risk_level, write_off_category,
    detected_faults_summary, saved,
  } = opportunity

  const translateX = useRef(new Animated.Value(0)).current
  const [revealed, setRevealed] = useState(false)
  const queryClient = useQueryClient()

  const showWriteOff = write_off_category && write_off_category !== 'clean'

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, { dx, dy }) =>
        Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy),
      onPanResponderMove: (_, { dx }) => {
        if (dx < 0) translateX.setValue(Math.max(dx, -100))
      },
      onPanResponderRelease: (_, { dx }) => {
        if (dx < SWIPE_THRESHOLD) {
          Animated.spring(translateX, { toValue: -80, useNativeDriver: true }).start()
          setRevealed(true)
        } else {
          Animated.spring(translateX, { toValue: 0, useNativeDriver: true }).start()
          setRevealed(false)
        }
      },
    })
  ).current

  const handleSave = async () => {
    await toggleSaved(id)
    Animated.spring(translateX, { toValue: 0, useNativeDriver: true }).start()
    setRevealed(false)
    queryClient.invalidateQueries({ queryKey: ['opportunities'] })
  }

  return (
    <View style={styles.wrapper}>
      <TouchableOpacity
        style={[styles.saveAction, { backgroundColor: saved ? colours.danger : colours.black }]}
        onPress={handleSave}
        activeOpacity={0.8}
      >
        <Text style={styles.saveActionText} allowFontScaling={false}>
          {saved ? '✕' : '↓'}
        </Text>
      </TouchableOpacity>

      <Animated.View
        style={[styles.card, { transform: [{ translateX }] }]}
        {...panResponder.panHandlers}
      >
        <TouchableOpacity
          onPress={() => router.push(`/opportunity/${id}`)}
          activeOpacity={0.95}
        >
          {/* Row 1: Logo + Car name + Class badge */}
          <View style={styles.topRow}>
            <CarLogo make={make} size={40} />
            <Text style={styles.carName} numberOfLines={1} allowFontScaling={true}>
              {make} {model} {year ?? ''}
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
      </Animated.View>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    marginHorizontal: 16,
    marginBottom: 8,
    overflow: 'hidden',
    borderRadius: 8,
  },
  saveAction: {
    position: 'absolute',
    right: 0,
    top: 0,
    bottom: 0,
    width: 80,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
  },
  saveActionText: {
    fontSize: 18,
    fontWeight: '700',
    color: colours.white,
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
