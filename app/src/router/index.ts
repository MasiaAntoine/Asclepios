import { createRouter, createWebHistory } from 'vue-router'
import ReportsView from '@/views/ReportsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
    },
    {
      path: '/profil',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
    },
    {
      path: '/profil/relations/:slug',
      name: 'relation-dossier',
      component: () => import('@/views/RelationDossierView.vue'),
    },
    {
      path: '/profil/personnes/:slug',
      name: 'personne-dossier',
      component: () => import('@/views/PersonneDossierView.vue'),
    },
    {
      path: '/rapports',
      name: 'reports',
      component: ReportsView,
    },
    {
      path: '/rapports/:slug',
      name: 'report-detail',
      component: () => import('@/views/ReportDetailView.vue'),
    },
    {
      path: '/poids',
      name: 'weight',
      component: () => import('@/views/WeightView.vue'),
    },
    {
      path: '/suivi',
      name: 'suivi',
      component: () => import('@/views/SuiviView.vue'),
    },
    { path: '/labs', redirect: { name: 'suivi', query: { tab: 'labs' } } },
    { path: '/rx', redirect: { name: 'suivi', query: { tab: 'rx' } } },
    {
      path: '/prise-de-sang',
      name: 'prise-de-sang',
      component: () => import('@/views/PriseDeSangView.vue'),
    },
    {
      path: '/prise-de-sang/:id',
      name: 'prise-de-sang-detail',
      component: () => import('@/views/PriseDeSangDetailView.vue'),
    },
    {
      path: '/ordonnances',
      name: 'ordonnances',
      component: () => import('@/views/OrdonnancesView.vue'),
    },
    {
      path: '/ordonnances/:id',
      name: 'ordonnances-detail',
      component: () => import('@/views/OrdonnancesDetailView.vue'),
    },
    {
      path: '/meds',
      name: 'meds',
      component: () => import('@/views/MedsView.vue'),
    },
    {
      path: '/meds/:id',
      name: 'med-doc',
      component: () => import('@/views/MedDocView.vue'),
    },
    {
      path: '/medecins',
      name: 'doctors',
      component: () => import('@/views/DoctorsView.vue'),
    },
    {
      path: '/assistant',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
  ],
})

export default router
