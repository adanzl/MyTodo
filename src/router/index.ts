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
        component: () => import('@/views/PageSchedule.vue')
      },
      {
        path: 'tab2',
        component: () => import('@/views/PageCalendar.vue')
      },
      {
        path: 'tab3',
        component: () => import('@/views/chat-page/PageChat.vue')
      },
      {
        path: 'tab4',
        component: () => import('@/views/lottery-page/PageLottery.vue')
      },
      {
        path: 'tab0',
        component: () => import('@/views/PageTimetable.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
