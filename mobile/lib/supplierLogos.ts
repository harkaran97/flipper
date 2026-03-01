/** Maps supplier names to their favicon/logo URLs for display in parts sections. */

export const SUPPLIER_LOGOS: Record<string, string> = {
  'GSF Car Parts': 'https://www.gsf.co.uk/favicon.ico',
  'Euro Car Parts': 'https://www.eurocarparts.com/favicon.ico',
  'The Parts People': 'https://thepartspeople.co.uk/favicon.ico',
  'Autodoc': 'https://www.autodoc.co.uk/favicon.ico',
  'eBay Motors Parts': 'https://www.ebay.co.uk/favicon.ico',
  'Andrew Page': 'https://www.andrewpage.co.uk/favicon.ico',
}

export const getSupplierLogo = (supplier: string): string | null =>
  SUPPLIER_LOGOS[supplier] ?? null
