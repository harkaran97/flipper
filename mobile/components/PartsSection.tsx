/**
 * Parts breakdown section for the detail screen.
 * Accordion grouped by fault. Top 2 eBay results per part.
 * Accordion grouped by fault — tap header to expand/collapse.
 * eBay URL fix: arrow only shown for valid, non-placeholder URLs.
 */
import React, { useState } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  Linking,
  StyleSheet,
  Platform,
  UIManager,
} from 'react-native'
import { FaultPartsBreakdown, PartResult, SupplierPrice } from '../lib/types'
import { formatPrice, formatFaultType } from '../lib/formatters'
import { SupplierLogo } from './SupplierLogo'
import { colours } from '../constants/colours'

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true)
}

function isValidPartUrl(url: string | null | undefined): boolean {
  if (!url || url.trim() === '') return false
  if (url.includes('sub_generic')) return false
  if (!url.startsWith('http')) return false
  return true
}

function handlePartTap(url: string | null | undefined) {
  if (!isValidPartUrl(url)) return
  Linking.openURL(url!)
}

// Consumable pill badge
function ConsumablePill() {
  return (
    <View style={styles.consumablePill}>
      <Text style={styles.consumableText}>consumable</Text>
    </View>
  )
}

// Single supplier row
function SupplierRow({ supplier }: { supplier: SupplierPrice }) {
  const valid = isValidPartUrl(supplier.url)
  const displayPrice = supplier.total_cost_pence > 0
    ? supplier.total_cost_pence
    : supplier.price_pence
  return (
    <TouchableOpacity
      style={styles.supplierRow}
      onPress={() => handlePartTap(supplier.url)}
      activeOpacity={valid ? 0.7 : 1}
      disabled={!valid}
    >
      <SupplierLogo supplier={supplier.supplier} size={16} />
      <Text style={styles.supplierName} numberOfLines={1} allowFontScaling={true}>
        {supplier.supplier}
      </Text>
      <Text style={styles.supplierPrice} allowFontScaling={true}>
        {formatPrice(displayPrice)}
      </Text>
      {valid && <Text style={styles.arrow} allowFontScaling={false}>→</Text>}
    </TouchableOpacity>
  )
}

// Single part block — name + top 2 suppliers
function PartBlock({ part }: { part: PartResult }) {
  const topSuppliers = part.suppliers.slice(0, 2)
  return (
    <View style={styles.partBlock}>
      <View style={styles.partHeaderRow}>
        <Text style={styles.partName} allowFontScaling={true}>{part.part_name}</Text>
        {part.is_consumable && <ConsumablePill />}
      </View>
      {topSuppliers.length === 0 ? (
        <Text style={styles.noSuppliersText}>No pricing available</Text>
      ) : (
        topSuppliers.map((s, i) => <SupplierRow key={i} supplier={s} />)
      )}
    </View>
  )
}

// Accordion item per fault group
function FaultAccordionItem({
  fault,
  initiallyOpen,
}: {
  fault: FaultPartsBreakdown
  initiallyOpen: boolean
}) {
  const [isOpen, setIsOpen] = useState(initiallyOpen)

  const toggle = () => {
    setIsOpen(prev => !prev)
  }

  const hasParts = fault.parts.length > 0
  const hasRange = fault.fault_parts_total_min_pence > 0

  return (
    <View style={styles.accordionItem}>
      {/* Header row — tappable */}
      <TouchableOpacity
        style={styles.accordionHeader}
        onPress={toggle}
        activeOpacity={0.7}
      >
        <Text style={styles.accordionChevron}>{isOpen ? '▼' : '▶'}</Text>
        <Text style={styles.accordionTitle} allowFontScaling={true}>
          {formatFaultType(fault.fault_type)}
        </Text>
      </TouchableOpacity>

      {/* Expandable content */}
      {isOpen && (
        <View style={styles.accordionContent}>
          {!hasParts ? (
            <Text style={styles.noPartsText}>No parts found</Text>
          ) : (
            <>
              {fault.parts.map((part, i) => (
                <PartBlock key={i} part={part} />
              ))}
              {hasRange && (
                <Text style={styles.estRange}>
                  Est. parts: {formatPrice(fault.fault_parts_total_min_pence)}–{formatPrice(fault.fault_parts_total_max_pence)}
                </Text>
              )}
            </>
          )}
        </View>
      )}
    </View>
  )
}

interface Props {
  breakdown: FaultPartsBreakdown[]
}

export const PartsSection: React.FC<Props> = ({ breakdown }) => {
  if (!breakdown || breakdown.length === 0) return null

  return (
    <View style={styles.container}>
      {breakdown.map((fault, idx) => (
        <FaultAccordionItem
          key={fault.fault_type}
          fault={fault}
          initiallyOpen={fault.parts.length > 0}
        />
      ))}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {},
  accordionItem: {
    borderBottomWidth: 0.5,
    borderBottomColor: 'rgba(60,60,67,0.13)',
  },
  accordionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    gap: 8,
  },
  accordionChevron: {
    fontSize: 10,
    color: colours.textMuted,
    width: 12,
  },
  accordionTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '600',
    color: colours.textPrimary,
  },
  accordionContent: {
    paddingBottom: 12,
    paddingLeft: 20,
  },
  partBlock: {
    marginBottom: 10,
  },
  partHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  partName: {
    fontSize: 14,
    fontWeight: '500',
    color: colours.textPrimary,
    flex: 1,
  },
  consumablePill: {
    backgroundColor: 'rgba(60,60,67,0.08)',
    borderRadius: 100,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  consumableText: {
    fontSize: 11,
    color: colours.textSecondary,
    fontWeight: '500',
  },
  supplierRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 5,
    gap: 7,
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
    fontVariant: ['tabular-nums'],
  },
  arrow: {
    fontSize: 14,
    color: colours.textMuted,
    width: 16,
    textAlign: 'right',
  },
  noSuppliersText: {
    fontSize: 13,
    color: colours.textMuted,
    fontStyle: 'italic',
  },
  noPartsText: {
    fontSize: 13,
    color: colours.textMuted,
    fontStyle: 'italic',
    paddingBottom: 4,
  },
  estRange: {
    fontSize: 13,
    color: colours.textMuted,
    fontStyle: 'italic',
    marginTop: 4,
  },
})
