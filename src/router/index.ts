import { createRouter, createWebHistory } from '@ionic/vue-router';
import { RouteRecordRaw } from 'vue-router';
import TabsPage from '../views/TabsPage.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/tabs/tab1'
  },
  {
    path: '/tabs/',
    component: TabsPage,
    children: [
      {
        path: '',
        redirect: '/tabs/tab1'
      },
      {
        path: 'tab1',
        component: () => import('@/views/TabSchedulePage.vue')
      },
      {
        path: 'tab2',
        component: () => import('@/views/TabCalendarPage.vue')
      },
      {
        path: 'tab3',
        component: () => import('@/views/TabChatPage.vue')
      },
      {
        path: 'tab4',
        component: () => import('@/views/TabLotteryPage.vue')
      },
      {
        path: 'tab0',
        component: () => import('@/views/TabSavePage.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
