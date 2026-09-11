// Mirrors core/resolver.py is_free_tier_supported (suffix half only -
// typed input has no region). Unknown suffixes default to supported.

// NOTE: kept in sync with _NON_US_SUFFIXES in core/resolver.py
const NON_US_SUFFIXES = new Set([
  'T', 'L', 'MX', 'NS', 'BO', 'PA', 'DE', 'F', 'TO', 'AX', 'HK',
  'SS', 'SZ', 'KS', 'KQ', 'SI', 'BK', 'JK', 'TW', 'TWO', 'OL', 'ST',
  'HE', 'CO', 'MI', 'AS', 'BR', 'LS', 'IR', 'VX', 'SW', 'VI', 'PR',
  'ME', 'AT', 'SA', 'BA', 'SN', 'NX', 'QA', 'KW', 'EG', 'MU', 'IS',
  'NE', 'CN', 'KL', 'J',
]);

export function isInternationalTicker(symbol: string): boolean {
  const sym = symbol.trim().toUpperCase();
  if (!sym.includes('.')) return false;
  const suffix = sym.split('.').pop() ?? '';
  return NON_US_SUFFIXES.has(suffix);
}
