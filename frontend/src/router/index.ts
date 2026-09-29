import { createRouter, createWebHistory } from 'vue-router';
import ExamPanel from '@/components/ExamPanel.vue';
import ManagePanel from '@/components/ManagePanel.vue';
import AnalysisPanel from '@/components/AnalysisPanel.vue';
import WrongAnalysis from '@/components/WrongAnalysis.vue';
import Settings from '@/components/Settings.vue';
import KnowledgeGraph from '@/components/KnowledgeGraph.vue';
import Dashboard from '@/components/Dashboard.vue';
import SrsPanel from '@/components/SrsPanel.vue';
import GraphWalk from '@/components/GraphWalk.vue';
const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/exam', name: 'Exam', component: ExamPanel },
  { path: '/analysis', name: 'Analysis', component: AnalysisPanel },
  { path: '/manage', name: 'Manage', component: ManagePanel },
  { path: '/wrong-analysis', name: 'WrongAnalysis', component: WrongAnalysis },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/knowledge', name: 'KnowledgeGraph', component: KnowledgeGraph },
  { path: '/srs', name: 'Srs', component: SrsPanel },
  { path: '/graph-walk', name: 'GraphWalk', component: GraphWalk },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;