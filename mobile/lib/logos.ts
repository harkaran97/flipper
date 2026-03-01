/**
 * Maps car manufacturer names to logo image URLs.
 * Uses the car-logos-dataset CDN hosted on GitHub.
 * Falls back to null if make is not found — always show something.
 */

const MAKE_LOGO_MAP: Record<string, string> = {
  'BMW': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/bmw.png',
  'Mercedes': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/mercedes-benz.png',
  'Mercedes-Benz': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/mercedes-benz.png',
  'Audi': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/audi.png',
  'Volkswagen': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/volkswagen.png',
  'VW': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/volkswagen.png',
  'Ford': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/ford.png',
  'Vauxhall': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/vauxhall.png',
  'Toyota': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/toyota.png',
  'Honda': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/honda.png',
  'Nissan': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/nissan.png',
  'Land Rover': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/land-rover.png',
  'Jaguar': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/jaguar.png',
  'Volvo': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/volvo.png',
  'Peugeot': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/peugeot.png',
  'Renault': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/renault.png',
  'Seat': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/seat.png',
  'Skoda': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/skoda.png',
  'Hyundai': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/hyundai.png',
  'Kia': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/kia.png',
  'Mazda': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/mazda.png',
  'Subaru': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/subaru.png',
  'Mitsubishi': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/mitsubishi.png',
  'Porsche': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/porsche.png',
  'Fiat': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/fiat.png',
  'Alfa Romeo': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/alfa-romeo.png',
  'Citroen': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/citroen.png',
  'Mini': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/mini.png',
  'Tesla': 'https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/thumb/tesla.png',
}

export { MAKE_LOGO_MAP }

export const getCarLogoUrl = (make: string): string | null =>
  MAKE_LOGO_MAP[make] ?? null
