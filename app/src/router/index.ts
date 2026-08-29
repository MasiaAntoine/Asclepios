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
  ],
})

export default router
