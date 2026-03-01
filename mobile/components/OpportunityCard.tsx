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
        style={[styles.saveAction, { backgroundColor: saved ? colours.riskHigh : colours.black }]}
        onPress={handleSave}
        activeOpacity={0.8}
      >
        <Text style={styles.saveActionText} allowFontScaling={false}>
          {saved ? '🗑' : '🔖'}
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
          <View style={styles.topRow}>
            <CarLogo make={make} size={40} />
            <View style={styles.nameBlock}>
              <Text style={styles.carName} numberOfLines={1} allowFontScaling={true}>
                {make} {model} {year ?? ''}
              </Text>
              <Text style={styles.askingPrice} allowFontScaling={true}>
                {formatPrice(listing_price_pence)} asking
              </Text>
            </View>
            <BadgeClass opportunityClass={opportunity_class} />
          </View>

          <View style={styles.profitRow}>
            <Text style={styles.profit} allowFontScaling={true}>
              {formatProfit(true_profit_pence)}
            </Text>
            <Text style={styles.days} allowFontScaling={true}>
              {' · '}{formatDays(total_man_days)}
            </Text>
          </View>

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
    marginBottom: 10,
    overflow: 'hidden',
    borderRadius: 12,
  },
  saveAction: {
    position: 'absolute',
    right: 0,
    top: 0,
    bottom: 0,
    width: 80,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
  },
  saveActionText: {
    fontSize: 24,
  },
  card: {
    backgroundColor: colours.bgCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colours.border,
    padding: 14,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
  },
  nameBlock: { flex: 1 },
  carName: {
    fontSize: 17,
    fontWeight: '600',
    color: colours.textPrimary,
  },
  askingPrice: {
    fontSize: 13,
    color: colours.textMuted,
    marginTop: 2,
  },
  profitRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  profit: {
    fontSize: 22,
    fontWeight: '700',
    color: colours.green,
  },
  days: {
    fontSize: 15,
    color: colours.textMuted,
  },
  bottomRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  faultSummary: {
    flex: 1,
    fontSize: 13,
    color: colours.textMuted,
  },
  badges: {
    flexDirection: 'row',
    gap: 6,
  },
  writeOffBadge: {
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  writeOffText: {
    fontSize: 11,
    fontWeight: '600',
    color: colours.white,
  },
})
