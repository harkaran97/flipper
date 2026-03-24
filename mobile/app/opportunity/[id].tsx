/**
 * Opportunity detail screen — Revolut-style information architecture.
 * Eye path: profit number → what's wrong → parts cost → CTA buttons.
 * Light mode. Single green accent (#34C759). F2F2F7 grouped background.
 */
import React, { useState, useEffect, useRef } from 'react'
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  Linking,
  StyleSheet,
  Animated,
  ActivityIndicator,
  Pressable,
} from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useLocalSearchParams } from 'expo-router'
import { useOpportunityDetail } from '../../hooks/useOpportunityDetail'
import { DetailHeader } from '../../components/DetailHeader'
import { FaultRow } from '../../components/FaultRow'
import { PartsSection } from '../../components/PartsSection'
import { colours } from '../../constants/colours'
import { formatPrice, formatDays } from '../../lib/formatters'
import { markAsBuildApi, unmarkAsBuildApi } from '../../lib/api'
import { useQueryClient } from '@tanstack/react-query'

const CONFIDENCE_COLOUR: Record<string, string> = {
  high: colours.green,
  medium: colours.amber,
  low: colours.riskHigh,
}

export default function OpportunityDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { data: opportunity, isLoading, isError } = useOpportunityDetail(id)
  const [isBuild, setIsBuild] = useState(false)
  const queryClient = useQueryClient()
  const insets = useSafeAreaInsets()

  // Scroll ref — force top on mount
  const scrollRef = useRef<ScrollView>(null)

  // Button press scale animations
  const primaryScale = useRef(new Animated.Value(1)).current
  const secondaryScale = useRef(new Animated.Value(1)).current

  useEffect(() => {
    if (opportunity) {
      setIsBuild(opportunity.marked_as_build ?? false)
    }
  }, [opportunity])

  useEffect(() => {
    // Force scroll to top on mount — prevents inheriting scroll position
    scrollRef.current?.scrollTo({ y: 0, animated: false })
  }, [])

  const handleToggleBuild = async () => {
    const next = !isBuild
    setIsBuild(next)
    if (next) {
      await markAsBuildApi(id)
    } else {
      await unmarkAsBuildApi(id)
    }
    queryClient.invalidateQueries({ queryKey: ['opportunities', 'builds'] })
    queryClient.invalidateQueries({ queryKey: ['opportunity', id] })
  }

  const pressIn = (anim: Animated.Value) =>
    Animated.spring(anim, { toValue: 0.97, useNativeDriver: true, speed: 30, bounciness: 0 }).start()
  const pressOut = (anim: Animated.Value) =>
    Animated.spring(anim, { toValue: 1, useNativeDriver: true, speed: 20, bounciness: 4 }).start()

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colours.green} />
      </View>
    )
  }

  if (isError || !opportunity) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Could not load opportunity.</Text>
      </View>
    )
  }

  const confidenceDot = CONFIDENCE_COLOUR[opportunity.market_value_confidence] ?? colours.textMuted

  const totalMin = opportunity.parts_cost_min_pence + opportunity.effort_cost_pence
  const totalMax = opportunity.parts_cost_max_pence + opportunity.effort_cost_pence

  return (
    <View style={styles.root}>
      <ScrollView
        ref={scrollRef}
        style={styles.scroll}
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: insets.bottom + 160 },
        ]}
        showsVerticalScrollIndicator={false}
      >
        {/* Hero card — car info + profit hero */}
        <View style={styles.card}>
          <DetailHeader opportunity={opportunity} />
        </View>

        {/* Market value compact row */}
        <View style={styles.card}>
          <View style={styles.cardPad}>
            <Text style={styles.sectionLabel}>MARKET VALUE</Text>
            <View style={styles.marketRow}>
              <Text style={styles.marketValueText}>
                {formatPrice(opportunity.market_value_pence)}
                <Text style={styles.marketMeta}> median</Text>
              </Text>
              <View style={[styles.confidenceDot, { backgroundColor: confidenceDot }]} />
            </View>
            <Text style={styles.marketSubtext}>
              {opportunity.market_value_comp_count} comps · {opportunity.market_value_confidence} confidence
            </Text>
          </View>
        </View>

        {/* What's Wrong section */}
        {opportunity.faults && opportunity.faults.length > 0 && (
          <View style={styles.card}>
            <View style={styles.cardPad}>
              <Text style={styles.sectionLabel}>WHAT'S WRONG</Text>
              {opportunity.faults.map((fault, idx) => (
                <FaultRow key={idx} fault={fault} />
              ))}
            </View>
          </View>
        )}

        {/* Parts Needed accordion */}
        {opportunity.parts_breakdown && opportunity.parts_breakdown.length > 0 && (
          <View style={styles.card}>
            <View style={styles.cardPad}>
              <Text style={styles.sectionLabel}>PARTS NEEDED</Text>
              <PartsSection breakdown={opportunity.parts_breakdown} />
            </View>
          </View>
        )}

        {/* Total estimate */}
        <View style={styles.card}>
          <View style={styles.cardPad}>
            <View style={styles.totalDivider} />
            <Text style={styles.sectionLabel}>TOTAL ESTIMATE</Text>
            <View style={styles.estimateRow}>
              <Text style={styles.estimateLabel}>Parts</Text>
              <Text style={styles.estimateValue}>
                {formatPrice(opportunity.parts_cost_min_pence)}–{formatPrice(opportunity.parts_cost_max_pence)}
              </Text>
            </View>
            <View style={styles.estimateRow}>
              <Text style={styles.estimateLabel}>Labour</Text>
              <Text style={styles.estimateValue}>
                {formatDays(opportunity.total_man_days)} @ {formatPrice(opportunity.day_rate_pence)}/day = {formatPrice(opportunity.effort_cost_pence)}
              </Text>
            </View>
            <View style={styles.estimateDivider} />
            <View style={styles.estimateRow}>
              <Text style={[styles.estimateLabel, styles.bold]}>Total</Text>
              <Text style={[styles.estimateValue, styles.bold]}>
                {formatPrice(totalMin)}–{formatPrice(totalMax)}
              </Text>
            </View>
            {opportunity.unpriced_fault_types && opportunity.unpriced_fault_types.length > 0 && (
              <Text style={styles.unpricedNote}>
                Excludes unpriced: {opportunity.unpriced_fault_types.join(', ')}
              </Text>
            )}
          </View>
        </View>

        <View style={{ height: 8 }} />
      </ScrollView>

      {/* Floating glass action buttons — above tab bar */}
      <View
        style={[
          styles.floatingActions,
          { bottom: insets.bottom + 80 },
        ]}
      >
        {/* 1px top light refraction */}
        <View style={styles.floatingActionsEdge} />

        {/* View on eBay — green filled */}
        <Animated.View style={[styles.buttonWrap, { transform: [{ scale: primaryScale }] }]}>
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => Linking.openURL(opportunity.listing_url)}
            onPressIn={() => pressIn(primaryScale)}
            onPressOut={() => pressOut(primaryScale)}
            activeOpacity={1}
          >
            <Text style={styles.primaryButtonText}>View on eBay</Text>
          </TouchableOpacity>
        </Animated.View>

        {/* Mark as Build — ghost outline */}
        <Animated.View style={[styles.buttonWrap, { transform: [{ scale: secondaryScale }] }]}>
          <TouchableOpacity
            style={[styles.secondaryButton, isBuild && styles.secondaryButtonActive]}
            onPress={handleToggleBuild}
            onPressIn={() => pressIn(secondaryScale)}
            onPressOut={() => pressOut(secondaryScale)}
            activeOpacity={1}
          >
            <Text style={[styles.secondaryButtonText, isBuild && styles.secondaryButtonTextActive]}>
              {isBuild ? 'Remove Build' : 'Mark as Build'}
            </Text>
          </TouchableOpacity>
        </Animated.View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colours.bgGrouped,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingTop: 12,
    paddingHorizontal: 16,
    gap: 12,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colours.bgGrouped,
  },
  errorText: {
    fontSize: 15,
    color: colours.textSecondary,
  },
  card: {
    backgroundColor: colours.white,
    borderRadius: 16,
    overflow: 'hidden',
  },
  cardPad: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 16,
  },
  sectionLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: colours.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 10,
  },
  // Market value
  marketRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  marketValueText: {
    fontSize: 17,
    fontWeight: '600',
    color: colours.textPrimary,
    fontVariant: ['tabular-nums'],
  },
  marketMeta: {
    fontSize: 15,
    fontWeight: '400',
    color: colours.textSecondary,
  },
  marketSubtext: {
    fontSize: 13,
    color: colours.textSecondary,
  },
  confidenceDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginLeft: 8,
  },
  // Total estimate
  totalDivider: {
    height: 1,
    backgroundColor: colours.border,
    marginBottom: 16,
  },
  estimateRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 5,
  },
  estimateLabel: {
    fontSize: 15,
    color: colours.textSecondary,
    minWidth: 60,
  },
  estimateValue: {
    fontSize: 15,
    color: colours.textPrimary,
    fontVariant: ['tabular-nums'],
    textAlign: 'right',
    flex: 1,
    marginLeft: 12,
  },
  estimateDivider: {
    height: 0.5,
    backgroundColor: 'rgba(60,60,67,0.13)',
    marginVertical: 8,
  },
  bold: {
    fontWeight: '700',
    color: colours.textPrimary,
  },
  unpricedNote: {
    fontSize: 12,
    color: colours.textMuted,
    fontStyle: 'italic',
    marginTop: 8,
  },
  // Floating glass action bar
  floatingActions: {
    position: 'absolute',
    left: 16,
    right: 16,
    flexDirection: 'row',
    gap: 10,
    backgroundColor: 'rgba(255,255,255,0.85)',
    borderRadius: 28,
    borderWidth: 0.5,
    borderColor: 'rgba(60,60,67,0.15)',
    padding: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 20,
    elevation: 10,
  },
  floatingActionsEdge: {
    position: 'absolute',
    top: 0,
    left: 12,
    right: 12,
    height: 0.5,
    backgroundColor: 'rgba(255,255,255,0.6)',
  },
  buttonWrap: {
    flex: 1,
  },
  primaryButton: {
    backgroundColor: colours.green,
    borderRadius: 22,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: colours.white,
    letterSpacing: -0.3,
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    borderRadius: 22,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(60,60,67,0.22)',
  },
  secondaryButtonActive: {
    backgroundColor: colours.black,
    borderColor: colours.black,
  },
  secondaryButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: colours.black,
    letterSpacing: -0.3,
  },
  secondaryButtonTextActive: {
    color: colours.white,
  },
})
