/**
 * Opportunity detail screen.
 * Full breakdown: faults, parts, market value, effort cost, and action buttons.
 * "View on eBay" opens the listing URL. "Mark as Build" toggles local build status.
 */
import React, { useState, useEffect } from 'react'
import {
  ScrollView, View, Text, TouchableOpacity, Linking,
  StyleSheet, SafeAreaView, ActivityIndicator,
} from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { useOpportunityDetail } from '../../hooks/useOpportunityDetail'
import { DetailHeader } from '../../components/DetailHeader'
import { FaultRow } from '../../components/FaultRow'
import { PartsSection } from '../../components/PartsSection'
import { colours } from '../../constants/colours'
import { formatPrice, formatDays } from '../../lib/formatters'
import { markAsBuild, removeFromBuild, getBuildStatuses } from '../../lib/storage'
import { useQueryClient } from '@tanstack/react-query'

export default function OpportunityDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { data: opportunity, isLoading, isError } = useOpportunityDetail(id)
  const [isBuild, setIsBuild] = useState(false)
  const queryClient = useQueryClient()

  useEffect(() => {
    getBuildStatuses().then(builds => {
      setIsBuild(builds[id] === 'active_build')
    })
  }, [id])

  const handleToggleBuild = async () => {
    if (isBuild) {
      await removeFromBuild(id)
    } else {
      await markAsBuild(id)
    }
    setIsBuild(prev => !prev)
    queryClient.invalidateQueries({ queryKey: ['opportunities'] })
  }

  if (isLoading) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={colours.green} />
      </SafeAreaView>
    )
  }

  if (isError || !opportunity) {
    return (
      <SafeAreaView style={styles.centered}>
        <Text style={styles.errorText} allowFontScaling={true}>
          Could not load opportunity.
        </Text>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <DetailHeader opportunity={opportunity} />

        <View style={styles.divider} />

        {/* Market value section */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel} allowFontScaling={true}>Market value</Text>
          <Text style={styles.marketValue} allowFontScaling={true}>
            {formatPrice(opportunity.market_value_pence)} median
            {' · '}{opportunity.market_value_comp_count} sold comps
            {' · '}{opportunity.market_value_confidence.charAt(0).toUpperCase() +
              opportunity.market_value_confidence.slice(1)} confidence
          </Text>
        </View>

        <View style={styles.divider} />

        {/* Faults section */}
        {opportunity.faults && opportunity.faults.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel} allowFontScaling={true}>What's wrong</Text>
            {opportunity.faults.map((fault, idx) => (
              <FaultRow key={idx} fault={fault} />
            ))}
          </View>
        )}

        {/* Parts section */}
        {opportunity.parts_breakdown && opportunity.parts_breakdown.length > 0 && (
          <>
            <View style={styles.divider} />
            <View style={styles.section}>
              <PartsSection breakdown={opportunity.parts_breakdown} />
            </View>
          </>
        )}

        {/* Effort cost section */}
        <View style={styles.divider} />
        <View style={styles.section}>
          <Text style={styles.sectionLabel} allowFontScaling={true}>Effort cost</Text>
          <Text style={styles.effortText} allowFontScaling={true}>
            {formatDays(opportunity.total_man_days)} × {formatPrice(opportunity.day_rate_pence)}/day
            {' = '}{formatPrice(opportunity.effort_cost_pence)}
          </Text>
        </View>

        {/* Unpriced faults */}
        {opportunity.unpriced_fault_types && opportunity.unpriced_fault_types.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.unpricedLabel} allowFontScaling={true}>
              Unpriced faults: {opportunity.unpriced_fault_types.join(', ')}
            </Text>
          </View>
        )}

        <View style={styles.bottomSpacer} />
      </ScrollView>

      {/* Sticky action buttons */}
      <View style={styles.actionBar}>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() => Linking.openURL(opportunity.listing_url)}
          activeOpacity={0.85}
        >
          <Text style={styles.primaryButtonText} allowFontScaling={false}>View on eBay</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.secondaryButton, isBuild && styles.secondaryButtonActive]}
          onPress={handleToggleBuild}
          activeOpacity={0.85}
        >
          <Text
            style={[styles.secondaryButtonText, isBuild && styles.secondaryButtonTextActive]}
            allowFontScaling={false}
          >
            {isBuild ? 'Remove Build' : 'Mark as Build'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colours.bg,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colours.bg,
  },
  errorText: {
    fontSize: 15,
    color: colours.textSecondary,
  },
  content: {
    padding: 20,
    paddingBottom: 100,
  },
  divider: {
    height: 1,
    backgroundColor: colours.border,
    marginVertical: 20,
  },
  section: {
    marginBottom: 4,
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: colours.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  marketValue: {
    fontSize: 15,
    color: colours.textPrimary,
    fontVariant: ['tabular-nums'],
  },
  effortText: {
    fontSize: 15,
    color: colours.textSecondary,
    fontVariant: ['tabular-nums'],
  },
  unpricedLabel: {
    fontSize: 13,
    color: colours.riskMedium,
  },
  bottomSpacer: {
    height: 40,
  },
  actionBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    gap: 10,
    padding: 16,
    paddingBottom: 32,
    backgroundColor: colours.bg,
    borderTopWidth: 1,
    borderTopColor: colours.border,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: colours.green,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: colours.white,
  },
  secondaryButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: colours.black,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
  },
  secondaryButtonActive: {
    backgroundColor: colours.black,
  },
  secondaryButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: colours.black,
  },
  secondaryButtonTextActive: {
    color: colours.white,
  },
})
