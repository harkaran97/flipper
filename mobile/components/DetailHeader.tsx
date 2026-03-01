/**
 * Detail screen header: car logo, name, asking price, profit hero,
 * classification badges, and optional unpriced faults warning.
 */
import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { OpportunityDetail } from '../lib/types'
import { formatPrice, formatProfit, formatDays } from '../lib/formatters'
import { CarLogo } from './CarLogo'
import { BadgeClass } from './BadgeClass'
import { BadgeRisk } from './BadgeRisk'
import { colours } from '../constants/colours'

interface Props {
  opportunity: OpportunityDetail
}

export const DetailHeader: React.FC<Props> = ({ opportunity }) => {
  const {
    make, model, year, listing_price_pence, true_profit_pence,
    true_margin_pct, total_man_days, opportunity_class, risk_level,
    write_off_category, has_unpriced_faults,
  } = opportunity

  const showWriteOff = write_off_category && write_off_category !== 'clean'

  return (
    <View>
      <View style={styles.logoRow}>
        <CarLogo make={make} size={56} />
        <View style={styles.titleBlock}>
          <Text style={styles.title} allowFontScaling={true}>
            {make} {model} {year ?? ''}
          </Text>
          <Text style={styles.askingPrice} allowFontScaling={true}>
            {formatPrice(listing_price_pence)} asking price
          </Text>
        </View>
      </View>

      <View style={styles.profitHero}>
        <Text style={styles.profit} allowFontScaling={true}>{formatProfit(true_profit_pence)}</Text>
        <Text style={styles.profitSub} allowFontScaling={true}>
          {true_margin_pct.toFixed(0)}% margin · {formatDays(total_man_days)} work
        </Text>
      </View>

      <View style={styles.badgeRow}>
        <BadgeClass opportunityClass={opportunity_class} />
        {showWriteOff && (
          <View style={[styles.writeOffBadge, {
            backgroundColor: write_off_category === 'Cat S' ? colours.catS : colours.catN
          }]}>
            <Text style={styles.writeOffText} allowFontScaling={true}>{write_off_category}</Text>
          </View>
        )}
        <BadgeRisk risk={risk_level} />
      </View>

      {has_unpriced_faults && (
        <View style={styles.warningBanner}>
          <Text style={styles.warningText} allowFontScaling={true}>
            ⚠ Profit estimate is a floor figure — some faults could not be priced.
          </Text>
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 16,
  },
  titleBlock: { flex: 1 },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: colours.textPrimary,
  },
  askingPrice: {
    fontSize: 14,
    color: colours.textSecondary,
    marginTop: 2,
  },
  profitHero: { marginBottom: 14 },
  profit: {
    fontSize: 32,
    fontWeight: '700',
    color: colours.green,
  },
  profitSub: {
    fontSize: 15,
    color: colours.textMuted,
    marginTop: 2,
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
    marginBottom: 14,
  },
  writeOffBadge: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  writeOffText: {
    fontSize: 11,
    fontWeight: '600',
    color: colours.white,
  },
  warningBanner: {
    backgroundColor: '#FFF8E1',
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: colours.speculative,
  },
  warningText: {
    fontSize: 13,
    color: '#795548',
  },
})
