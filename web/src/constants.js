export const KIND_FIELDS = {
  tax: ['person_name', 'address', 'phone', 'declared_income', 'tax_paid', 'filer_status'],
  vehicle: ['person_name', 'address', 'vehicle_reg_no', 'engine_capacity_cc', 'vehicle_make_model', 'registration_year'],
  utility: ['person_name', 'address', 'meter_ref_no', 'monthly_bill', 'connection_type'],
  property: ['person_name', 'seller_name', 'address', 'registry_no', 'property_value', 'transfer_date', 'area_marla', 'property_type'],
  generic: ['person_name', 'address', 'phone'],
}

export const FIELD_LABELS = {
  person_name: 'Person name',
  seller_name: 'Seller name',
  address: 'Address',
  phone: 'Phone',
  declared_income: 'Declared income',
  tax_paid: 'Tax paid',
  filer_status: 'Filer status',
  vehicle_reg_no: 'Vehicle reg no',
  engine_capacity_cc: 'Engine capacity',
  vehicle_make_model: 'Vehicle model',
  registration_year: 'Registration year',
  meter_ref_no: 'Meter ref no',
  monthly_bill: 'Monthly bill',
  connection_type: 'Connection type',
  registry_no: 'Registry no',
  property_value: 'Property value',
  transfer_date: 'Transfer date',
  area_marla: 'Area marla',
  property_type: 'Property type',
}

export const KIND_OPTIONS = ['tax', 'vehicle', 'utility', 'property', 'generic']
export const TIER_ORDER = ['critical', 'red', 'orange', 'yellow', 'green']
export const TIER_LABELS = { critical: 'Critical', red: 'High', orange: 'Medium', yellow: 'Low', green: 'Clean' }
export const DISPLAY_TIER_ORDER = ['critical', 'red', 'orange']

export const NODE_TYPES = [
  { key: 'Person', label: 'Person', color: '#1a2b4a', shape: 'circle' },
  { key: 'Vehicle', label: 'Vehicle', color: '#3d6b52', shape: 'square' },
  { key: 'Property', label: 'Property', color: '#d4b876', shape: 'diamond' },
  { key: 'Meter', label: 'Utility meter', color: '#5e5c58', shape: 'triangle' },
  { key: 'TaxReturn', label: 'Tax return', color: '#7a9e7e', shape: 'circle' },
  { key: 'OffshoreEntity', label: 'Offshore entity', color: '#c88a2a', shape: 'hexagon' },
  { key: 'Address', label: 'Address', color: '#a64b2a', shape: 'square' },
  { key: 'PhoneNumber', label: 'Phone number', color: '#7d5a44', shape: 'square' },
]

export const EDGE_TYPES = [
  { key: 'USES_ADDRESS', label: 'Uses address', color: '#a64b2a', dash: '0' },
  { key: 'USES_PHONE', label: 'Uses phone', color: '#7d5a44', dash: '0' },
  { key: 'FILED_IN', label: 'Filed tax return', color: '#7a9e7e', dash: '0' },
  { key: 'OWNS_VEHICLE', label: 'Owns vehicle', color: '#3d6b52', dash: '0' },
  { key: 'HAS_UTILITY_METER', label: 'Has utility meter', color: '#5e5c58', dash: '0' },
  { key: 'BOUGHT_PROPERTY', label: 'Bought property', color: '#d4b876', dash: '0' },
  { key: 'LINKED_TO_OFFSHORE_ENTITY', label: 'Offshore link', color: '#c88a2a', dash: '0' },
  { key: 'SAME_ADDRESS_AS', label: 'Same address', color: '#1a2b4a', dash: '4 4' },
  { key: 'SHARES_PHONE_WITH', label: 'Shares phone', color: '#3d6b52', dash: '2 2' },
]

export const BENFORD_EXPECTED = {
  1: 0.301,
  2: 0.176,
  3: 0.125,
  4: 0.097,
  5: 0.079,
  6: 0.067,
  7: 0.058,
  8: 0.051,
  9: 0.046,
}
