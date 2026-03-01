/**
 * Parts breakdown section for the detail screen.
 * Groups parts by fault, shows supplier rows with logos and prices,
 * and links each supplier row to its URL in the device browser.
 */
import React from 'react'
import { View, Text, TouchableOpacity, Linking, StyleSheet } from 'react-native'
import { FaultPartsBreakdown } from '../lib/types'
import { formatPrice, formatFaultType } from '../lib/formatters'
import { SupplierLogo } from './SupplierLogo'
import { colours } from '../constants/colours'

interface Props {
  breakdown: FaultPartsBreakdown[]
}

export const PartsSection: React.FC<Props> = ({ breakdown }) => {
  if (!breakdown || breakdown.length === 0) return null

  return (
    <View style={styles.container}>
      <Text style={styles.sectionTitle} allowFontScaling={true}>Parts needed</Text>
      {breakdown.map(fault => (
        <View key={fault.fault_type} style={styles.faultGroup}>
          <Text style={styles.faultTitle} allowFontScaling={true}>
            {formatFaultType(fault.fault_type)}
          </Text>
          {fault.parts.map((part, partIdx) => (
            <View key={partIdx} style={styles.partBlock}>
              <View style={styles.partHeader}>
                <Text style={styles.partName} allowFontScaling={true}>
                  {part.part_name}
                  {part.is_consumable ? (
                    <Text style={styles.consumable}> — consumable</Text>
                  ) : null}
                </Text>
              </View>
              {part.suppliers.map((supplier, sIdx) => (
                <TouchableOpacity
                  key={sIdx}
                  style={styles.supplierRow}
                  onPress={() => Linking.openURL(supplier.url)}
                  activeOpacity={0.7}
                >
                  <SupplierLogo supplier={supplier.supplier} />
                  <Text style={styles.supplierName} numberOfLines={1} allowFontScaling={true}>
                    {supplier.supplier}
                  </Text>
                  <Text style={styles.supplierPrice} allowFontScaling={true}>
                    {formatPrice(supplier.price_pence)}
                  </Text>
                  <Text style={styles.arrow} allowFontScaling={false}> →</Text>
                </TouchableOpacity>
              ))}
              {fault.fault_parts_total_min_pence > 0 && (
                <Text style={styles.faultTotal} allowFontScaling={true}>
                  Est. parts: {formatPrice(fault.fault_parts_total_min_pence)}–{formatPrice(fault.fault_parts_total_max_pence)}
                </Text>
              )}
            </View>
          ))}
        </View>
      ))}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { marginTop: 24 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '500',
    color: colours.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  faultGroup: {
    marginBottom: 20,
  },
  faultTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: colours.textPrimary,
    marginBottom: 8,
  },
  partBlock: {
    marginBottom: 12,
  },
  partHeader: {
    marginBottom: 4,
  },
  partName: {
    fontSize: 14,
    fontWeight: '500',
    color: colours.textPrimary,
  },
  consumable: {
    fontWeight: '400',
    color: colours.textMuted,
    fontSize: 13,
  },
  supplierRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    gap: 8,
  },
  supplierName: {
    flex: 1,
    fontSize: 14,
    color: colours.textSecondary,
  },
  supplierPrice: {
    fontSize: 14,
    fontWeight: '600',
    color: colours.textPrimary,
  },
  arrow: {
    fontSize: 14,
    color: colours.textMuted,
  },
  faultTotal: {
    fontSize: 13,
    color: colours.textMuted,
    marginTop: 4,
    fontStyle: 'italic',
  },
})
