/** TypeScript types mirroring the Flipper backend Pydantic schemas. */

export type OpportunityClass = 'strong' | 'speculative' | 'worth_a_look' | 'exclude'
export type RiskLevel = 'low' | 'medium' | 'high'
export type MarketValueConfidence = 'high' | 'medium' | 'low'

export interface OpportunityCard {
  id: string
  listing_id: string
  title: string
  make: string
  model: string
  year: number | null
  listing_url: string
  listing_price_pence: number
  parts_cost_min_pence: number
  parts_cost_max_pence: number
  market_value_pence: number
  true_profit_pence: number
  true_margin_pct: number
  total_man_days: number
  opportunity_class: OpportunityClass
  risk_level: RiskLevel
  write_off_category: string
  has_unpriced_faults: boolean
  profit_is_floor_estimate: boolean
  market_value_confidence: MarketValueConfidence
  market_value_comp_count: number
  created_at: string
  // local only
  saved?: boolean
  status?: 'new' | 'saved' | 'active_build'
  detected_faults_summary?: string
}

export interface SupplierPrice {
  supplier: string
  price_pence: number
  url: string
  in_stock: boolean
}

export interface PartResult {
  part_name: string
  part_category: string
  quantity: string
  is_consumable: boolean
  suppliers: SupplierPrice[]
}

export interface FaultPartsBreakdown {
  fault_type: string
  parts: PartResult[]
  fault_parts_total_min_pence: number
  fault_parts_total_max_pence: number
}

export interface FaultDetail {
  fault_type: string
  severity: string
  description: string | null
  labour_days: number
}

export interface OpportunityDetail extends OpportunityCard {
  faults: FaultDetail[]
  parts_breakdown: FaultPartsBreakdown[]
  effort_cost_pence: number
  day_rate_pence: number
  unpriced_fault_types: string[]
  linkup_fallback_used: boolean
}
