/** Chemins relatifs au vault, servis sous `/vault`. */

export const VAULT = {
  profil: 'identite/profil.json',
  photo: 'identite/profil.png',
  signature: 'identite/signature.png',
  poids: 'suivi/poids.csv',
  labs: 'suivi/labs.csv',
  labsConfig: 'suivi/labs-config.json',
  traitements: 'suivi/traitements.json',
  medicationConfig: 'suivi/medication-config.json',
  doctors: 'humains/medecins/doctors.json',
  rapportsIndex: 'rapports/index.json',
} as const

export function rapportFile(file: string): string {
  return `rapports/${file}`
}

export function personneFile(file: string): string {
  return `humains/personnes/${file}`
}

export function relationFile(file: string): string {
  return `humains/relations/${file}`
}
