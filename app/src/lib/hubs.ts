export type HubId = 'suivi' | 'documents' | 'dossier'

export interface HubTab {
  label: string
  to: string
  match: (path: string, queryTab?: string) => boolean
}

export const HUB_TABS: Record<HubId, HubTab[]> = {
  suivi: [
    {
      label: 'Analyses',
      to: '/suivi',
      match: (path, tab) => path.startsWith('/suivi') && tab !== 'rx',
    },
    {
      label: 'Traitement',
      to: '/suivi?tab=rx',
      match: (path, tab) => path.startsWith('/suivi') && tab === 'rx',
    },
    {
      label: 'Poids',
      to: '/poids',
      match: (path) => path.startsWith('/poids'),
    },
    {
      label: 'Humeur',
      to: '/humeur',
      match: (path) => path.startsWith('/humeur'),
    },
    {
      label: 'Sport',
      to: '/sport',
      match: (path) => path.startsWith('/sport'),
    },
    {
      label: 'Agenda',
      to: '/agenda',
      match: (path) => path.startsWith('/agenda'),
    },
  ],
  documents: [
    {
      label: 'Rapports',
      to: '/rapports',
      match: (path) => path.startsWith('/rapports'),
    },
    {
      label: 'Ordonnances',
      to: '/ordonnances',
      match: (path) => path.startsWith('/ordonnances'),
    },
    {
      label: 'Prise de sang',
      to: '/prise-de-sang',
      match: (path) => path.startsWith('/prise-de-sang'),
    },
  ],
  dossier: [
    {
      label: 'Profil',
      to: '/profil',
      match: (path) => path.startsWith('/profil'),
    },
    {
      label: 'Médecins',
      to: '/medecins',
      match: (path) => path.startsWith('/medecins'),
    },
    {
      label: 'Médicaments',
      to: '/meds',
      match: (path) => path.startsWith('/meds'),
    },
  ],
}

export function hubForPath(path: string): HubId | null {
  if (
    path.startsWith('/suivi') ||
    path.startsWith('/poids') ||
    path.startsWith('/humeur') ||
    path.startsWith('/sport') ||
    path.startsWith('/agenda')
  ) {
    return 'suivi'
  }
  if (
    path.startsWith('/rapports') ||
    path.startsWith('/ordonnances') ||
    path.startsWith('/prise-de-sang')
  ) {
    return 'documents'
  }
  if (
    path.startsWith('/profil') ||
    path.startsWith('/medecins') ||
    path.startsWith('/meds')
  ) {
    return 'dossier'
  }
  return null
}
