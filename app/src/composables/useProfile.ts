import { computed, ref } from 'vue'
import { dataUrl, fetchJson, fetchText } from '@/lib/dataClient'

export interface Personne {
  prenom: string
  nom: string
  date_naissance?: string
  lien?: string
  personne_de_confiance?: boolean
}

export interface Animal {
  nom: string
  espece: string
  race?: string
  date_naissance?: string
}

export interface RelationSuite {
  prenom?: string | null
  nom?: string | null
  /** sexuelle_ponctuelle | tromperie | revue (legacy: plan_cul) */
  lien: string
  note?: string | null
}

export interface RelationPassee {
  prenom: string
  nom?: string | null
  duree?: string | null
  debut?: string | null
  fin?: string | null
  note?: string | null
  /** Fichier MD dans data/relations/ (contexte narratif). */
  dossier?: string | null
  /** Personnes / plans après la relation (contexte, pas inventaire). */
  apres?: RelationSuite[]
}

export interface VieAmoureuse {
  note?: string
  premiere_vers?: string
  estimation_totale?: string
}

export interface CarteVitaleVerso {
  periode: string
  type: string
  fabricant: string
  numero: string
  indice?: string
}

export interface SecuriteSociale {
  nir: string
  carte_vitale_emise_le?: string
  carte_vitale_verso?: CarteVitaleVerso
}

export interface MutuelleValidite {
  debut: string
  fin: string
}

export interface MutuelleContact {
  email?: string
  telephone?: string
  fax?: string
  site?: string
  viamedis_tel?: string
  viamedis_pec?: string
  espace_ps?: string
}

export interface Mutuelle {
  organisme: string
  unite_gestion?: string
  adresse?: string
  numero_amc?: string
  numero_adherent?: string
  type_convention?: string
  roc?: string
  numero_teletransmission?: string
  reseau_tiers_payant?: string
  validite?: MutuelleValidite
  carte_imprimee_le?: string
  contact?: MutuelleContact
  garanties_tiers_payant?: Record<string, string>
  document?: string
  notice_md?: string
  contrat_pdf?: string
}

export interface Profil {
  prenom: string
  nom: string
  date_naissance: string
  sexe: string
  taille_cm: number
  securite_sociale?: SecuriteSociale
  mutuelle?: Mutuelle
  tabac: {
    type: string
    debut: string
    nicotine_mg_ml?: number
    note?: string
  }
  parents: {
    pere: Personne
    mere: Personne
  }
  fratrie: Personne[]
  entourage: Personne[]
  animaux: Animal[]
  vie_amoureuse?: VieAmoureuse
  relations_passees?: RelationPassee[]
}

export interface HistoriqueDose {
  date: string
  dose: string
  posologie: string
  evenement: string
  note: string
}

export interface Traitement {
  id: string
  nom: string
  forme: string
  si_besoin: boolean
  moment: string
  source?: string
  doc?: string
  historique: HistoriqueDose[]
}

export interface PoidsEntry {
  date: string
  poids_kg: number
}

function parseFrDate(d: string): Date | null {
  const m = d.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (!m) return null
  return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]))
}

function formatAge(dateNaissance: string): number | null {
  const birth = parseFrDate(dateNaissance)
  if (!birth) return null
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const m = today.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
  return age
}

function ageParts(dateNaissance: string): { years: number; months: number } | null {
  const birth = parseFrDate(dateNaissance)
  if (!birth) return null
  const today = new Date()
  let years = today.getFullYear() - birth.getFullYear()
  let months = today.getMonth() - birth.getMonth()
  if (today.getDate() < birth.getDate()) months -= 1
  if (months < 0) {
    years -= 1
    months += 12
  }
  if (years < 0) return null
  return { years, months }
}

/** Affiche « né le JJ/MM/AAAA · X ans Y mois » si date valide. */
export function ageLabel(dateNaissance: string | null | undefined): string | null {
  if (!dateNaissance) return null
  const parts = ageParts(dateNaissance)
  if (!parts) return `né le ${dateNaissance}`
  const { years, months } = parts
  const bits: string[] = []
  if (years > 0) bits.push(`${years} an${years > 1 ? 's' : ''}`)
  if (months > 0 || years === 0) bits.push(`${months} mois`)
  return `né le ${dateNaissance} · ${bits.join(' ')}`
}

function parsePoidsCsv(raw: string): PoidsEntry[] {
  return raw
    .trim()
    .split('\n')
    .slice(1)
    .map((line) => {
      const [date, poids] = line.split(',')
      return { date: date.trim(), poids_kg: parseFloat(poids) }
    })
    .filter((e) => e.date && !Number.isNaN(e.poids_kg))
}

function currentDose(t: Traitement): HistoriqueDose | null {
  if (!t.historique.length) return null
  return t.historique[t.historique.length - 1]
}

function isActive(t: Traitement): boolean {
  const last = currentDose(t)
  if (!last) return false
  if (last.evenement === 'arret') return false
  const doseNum = parseFloat(last.dose.replace(',', '.'))
  return !Number.isNaN(doseNum) ? doseNum > 0 : last.evenement !== 'arret'
}

function calcImc(poidsKg: number, tailleCm: number): number {
  const m = tailleCm / 100
  return poidsKg / (m * m)
}

function imcLabel(imc: number): string {
  if (imc < 18.5) return 'Insuffisance pondérale'
  if (imc < 25) return 'Normale'
  if (imc < 30) return 'Surpoids'
  return 'Obésité'
}

const profil = ref<Profil | null>(null)
const traitements = ref<Traitement[]>([])
const traitementsMisAJour = ref('')
const poids = ref<PoidsEntry[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let loaded = false

async function load() {
  if (loaded || loading.value) return
  loading.value = true
  error.value = null
  try {
    const [profilData, traitementsFile, poidsRaw] = await Promise.all([
      fetchJson<Profil>('profil.json'),
      fetchJson<{ traitements: Traitement[]; mis_a_jour: string }>('traitements.json'),
      fetchText('poids.csv'),
    ])
    profil.value = profilData
    traitements.value = traitementsFile.traitements
    traitementsMisAJour.value = traitementsFile.mis_a_jour
    poids.value = parsePoidsCsv(poidsRaw)
    loaded = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
  } finally {
    loading.value = false
  }
}

export async function reloadProfile() {
  loaded = false
  return load()
}

export function useProfile() {
  if (!loaded && !loading.value) void load()

  const age = computed(() =>
    profil.value ? formatAge(profil.value.date_naissance) : null,
  )
  const dernierPoids = computed(() =>
    poids.value.length ? poids.value[poids.value.length - 1] : null,
  )
  const imc = computed(() => {
    if (!profil.value || !dernierPoids.value) return null
    return calcImc(dernierPoids.value.poids_kg, profil.value.taille_cm)
  })

  const traitementsActifs = computed(() =>
    traitements.value
      .filter(isActive)
      .map((t) => ({ ...t, actuel: currentDose(t)! })),
  )

  const traitementsArretes = computed(() =>
    traitements.value
      .filter((t) => !isActive(t))
      .map((t) => ({ ...t, actuel: currentDose(t) })),
  )

  /** Photo served from private data volume — not shipped in the app repo */
  const photoUrl = computed(() => dataUrl('profil.png'))

  return {
    profil,
    photoUrl,
    age,
    poids,
    dernierPoids,
    imc,
    imcLabel: computed(() => (imc.value != null ? imcLabel(imc.value) : null)),
    traitements,
    traitementsActifs,
    traitementsArretes,
    traitementsMisAJour,
    loading,
    error,
    load,
    reload: reloadProfile,
    currentDose,
    isActive,
  }
}
