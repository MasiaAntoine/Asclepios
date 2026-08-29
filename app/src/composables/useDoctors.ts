import { ref } from 'vue'
import { dataUrl, fetchJson } from '@/lib/dataClient'

export interface DoctorAddress {
  voie: string
  code_postal: string
  ville: string
}

export interface DoctorTarif {
  label: string
  valeur: string
}

export interface DoctorFormation {
  annee: number | null
  label: string
}

export interface DoctorExperience {
  depuis: number | null
  label: string
}

export interface DoctorInfosLegales {
  rpps?: string
  adeli?: string
  siren?: string
  siret?: string
}

export interface DoctorLangue {
  langue: string
  niveau?: string
}

export interface Doctor {
  id: string
  prenom: string
  nom: string
  titre: string
  specialite: string
  role?: string
  photo: string | null
  doctolib?: string
  site_web?: string
  email?: string
  adresse?: DoctorAddress
  telephone?: string
  langues?: (string | DoctorLangue)[]
  presentation?: string
  approches?: string[]
  tarifs?: DoctorTarif[]
  convention?: string
  tiers_payant?: string
  carte_vitale?: boolean
  paiements?: string[]
  modalites?: string[]
  affiliations?: string[]
  formations?: DoctorFormation[]
  experiences?: DoctorExperience[]
  infos_legales?: DoctorInfosLegales
  notes?: string
}

interface DoctorsFile {
  medecins: Doctor[]
}

const doctors = ref<Doctor[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let loaded = false

async function load() {
  if (loaded || loading.value) return
  loading.value = true
  error.value = null
  try {
    const data = await fetchJson<DoctorsFile>('doctors.json')
    doctors.value = data.medecins ?? []
    loaded = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur de chargement'
    doctors.value = []
  } finally {
    loading.value = false
  }
}

export function useDoctors() {
  if (!loaded && !loading.value) void load()

  return { doctors, loading, error, reload: () => { loaded = false; return load() } }
}

export function doctorPhotoUrl(doctor: Doctor): string | null {
  if (!doctor.photo) return null
  if (doctor.photo.startsWith('http')) return doctor.photo
  return dataUrl(doctor.photo)
}

export function doctorFullName(doctor: Doctor): string {
  return [doctor.titre, doctor.prenom, doctor.nom].filter(Boolean).join(' ')
}
