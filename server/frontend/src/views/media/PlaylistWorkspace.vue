<template>
  <el-tabs v-model="tab">
    <el-tab-pane label="Weekly" name="weekly">
      <slot v-if="tab === 'weekly'" :calendar="false" />
    </el-tab-pane>
    <el-tab-pane label="Calendar 列表" name="calendar-list">
      <el-button type="primary" class="mb-3" :loading="saving" @click="createCalendar">新建日期排期</el-button>
      <el-table :data="calendarItems" row-key="id" empty-text="暂无 Calendar 排期">
        <el-table-column prop="name" label="播放列表" />
        <el-table-column prop="start_date" label="开始日期" />
        <el-table-column prop="end_date" label="结束日期（含当天）" />
        <el-table-column prop="start_time" label="开始时间" />
        <el-table-column label="设备"><template #default="{row}">{{ row.device?.name || row.device?.address || '未设置' }}</template></el-table-column>
        <el-table-column label="启用" width="100"><template #default="{row}"><el-switch :model-value="row.status === 1" :disabled="saving" @change="(v: string | number | boolean) => toggle(row, Boolean(v))" /></template></el-table-column>
        <el-table-column width="180"><template #default="{row}"><el-button @click="edit(row)">编辑</el-button><el-button type="danger" :disabled="saving" @click="removeCalendar(row)">删除</el-button></template></el-table-column>
      </el-table>
    </el-tab-pane>
    <el-tab-pane label="日历视图" name="calendar">
      <el-alert v-if="calendarError" :title="calendarError" type="error" :closable="false" />
      <el-calendar v-model="month" v-loading="calendarLoading">
        <template #date-cell="{data}">
          <div>{{ data.day.slice(-2) }}</div>
          <button v-for="event in byDay[data.day] || []" :key="event.id + event.start"
            class="block text-left text-xs text-blue-600 truncate w-full" @click.stop="selectEvent(event.id)">
            {{ event.start.slice(11,19) }}{{ event.occurrence_count > 1 ? ` ×${event.occurrence_count}` : '' }} {{ event.mode === 'weekly' ? '周' : '日' }} · {{ event.name }}
          </button>
        </template>
      </el-calendar>
    </el-tab-pane>
  </el-tabs>
  <el-drawer v-model="editorOpen" title="编辑 Calendar 排期" size="90%" destroy-on-close>
    <el-form v-if="draft" label-width="110px" class="border rounded p-3 mb-3" @submit.prevent="saveDraft">
      <el-form-item label="启用"><el-switch :model-value="draft.status === 1" @change="(v: string | number | boolean) => draft && (draft.status = v ? 1 : 0)" /></el-form-item>
      <el-form-item label="起止日期">
        <el-date-picker v-model="draft.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
        <span class="mx-2">至</span><el-date-picker v-model="draft.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期（包含当天）" />
      </el-form-item>
      <el-form-item label="开始时间"><el-time-picker v-model="draft.start_time" value-format="HH:mm:ss" /></el-form-item>
      <el-form-item label="持续分钟"><el-input-number v-model="draft.schedule.duration" :min="0" /><span class="ml-2">0 表示前置曲目与正片总时长</span></el-form-item>
      <el-form-item><el-button type="primary" :loading="saving" @click="saveDraft">保存排期</el-button><span class="ml-3 text-xs">同设备排期不能重叠；相邻时段允许首尾相接。</span></el-form-item>
    </el-form>
    <slot v-if="editorOpen && tab === 'calendar-list' && draft?.id === activeId" :calendar="true" />
  </el-drawer>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { api } from '@/api/config';
import { deletePlaylist, getPlaylist, updatePlaylist } from '@/api/api-playlist';
import { createPlaylistId } from '@/utils/playlist';
import type { Playlist } from '@/types/playlist';
interface Event { id: string; name: string; mode: string; start: string; end: string | null; occurrence_count: number }
const props = defineProps<{items: Playlist[]; activeId: string}>();
const emit = defineEmits<{select: [id: string]; saved: []}>();
const tab = ref('weekly'), saving = ref(false), calendarLoading = ref(false), calendarError = ref('');
const month = ref(new Date()), events = ref<Event[]>([]), draft = ref<Playlist | null>(null);
const editorOpen = ref(false), lastWeeklyId = ref(''), draftBaseline = ref('');
const calendarItems = computed(() => props.items.filter(row => row.mode === 'calendar'));
const weeklyItems = computed(() => props.items.filter(row => row.mode !== 'calendar'));
function scheduleFields(row: Playlist) {
  return {status: row.status, start_date: row.start_date, end_date: row.end_date,
    start_time: row.start_time, duration: row.schedule.duration};
}
function resetDraft(row: Playlist) {
  draft.value = JSON.parse(JSON.stringify(row));
  draftBaseline.value = JSON.stringify(scheduleFields(row));
}
watch(() => props.items.find(row => row.id === props.activeId), row => {
  if (row?.mode !== 'calendar') { if (row) lastWeeklyId.value = row.id; return; }
  if (draft.value?.id !== row.id) return;
  if (JSON.stringify(scheduleFields(draft.value)) === draftBaseline.value) resetDraft(row);
  else if (JSON.stringify(scheduleFields(row)) === draftBaseline.value) draft.value._revision = row._revision;
}, {immediate: true});
watch([tab, weeklyItems, () => props.activeId], () => {
  if (tab.value !== 'weekly') return;
  editorOpen.value = false;
  if (!weeklyItems.value.some(row => row.id === props.activeId)) {
    const row = weeklyItems.value.find(row => row.id === lastWeeklyId.value) || weeklyItems.value[0];
    if (row) emit('select', row.id);
  }
}, {immediate: true});
watch([() => props.items, editorOpen, () => draft.value?.id], () => {
  const id = draft.value?.id;
  if (editorOpen.value && tab.value === 'calendar-list' && id !== props.activeId && props.items.some(row => row.id === id)) {
    emit('select', id!);
  }
});
function edit(row: Playlist) {
  tab.value = 'calendar-list';
  resetDraft(row);
  emit('select', row.id);
  editorOpen.value = true;
}
async function submit(row: Playlist) {
  saving.value = true;
  try {
    const response = await updatePlaylist({id: row.id, _revision: row._revision, mode: 'calendar',
      status: row.status || 0, start_date: row.start_date, end_date: row.end_date, start_time: row.start_time,
      schedule: {enabled: row.status || 0, duration: row.schedule.duration, cron: row.schedule.cron}});
    if (response.code !== 0) throw new Error(response.msg);
    const refreshed = await getPlaylist(row.id);
    const canonical = (refreshed.data as Record<string, Playlist> | undefined)?.[row.id];
    if (canonical && draft.value?.id === row.id) resetDraft(canonical);
    emit('saved');
    ElMessage.success('已保存');
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '保存失败'); }
  finally { saving.value = false; }
}
async function createCalendar() {
  saving.value = true;
  try {
    const today = isoLocal(new Date()), id = createPlaylistId();
    const response = await updatePlaylist({id, name: '日期播放列表', mode: 'calendar', status: 0,
      start_date: today, end_date: today, start_time: '09:00:00', pre_list: [], playlist: [],
      pre_lists: Array.from({length: 7}, () => []), schedule: {enabled: 0, duration: 0, cron: ''}});
    if (response.code !== 0) throw new Error(response.msg);
    const refreshed = await getPlaylist(id);
    if (refreshed.code !== 0) throw new Error(refreshed.msg);
    const row = (refreshed.data as Record<string, Playlist>)[id];
    emit('saved');
    edit(row);
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '创建失败'); }
  finally { saving.value = false; }
}
function toggle(row: Playlist, enabled: boolean) { return submit({...row, status: enabled ? 1 : 0}); }
async function removeCalendar(row: Playlist) {
  try { await ElMessageBox.confirm(`删除日期排期「${row.name}」？`, '删除排期', {type: 'warning'}); }
  catch { return; }
  saving.value = true;
  try {
    const saved = await deletePlaylist(row.id, row._revision);
    if (saved.code !== 0) throw new Error(saved.msg);
    if (draft.value?.id === row.id) editorOpen.value = false;
    emit('saved');
    ElMessage.success('已删除');
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '删除失败'); }
  finally { saving.value = false; }
}
function saveDraft() { if (draft.value) return submit(draft.value); }
function selectEvent(id: string) {
  const row = props.items.find(v => v.id === id);
  if (!row) return;
  if (row.mode === 'calendar') edit(row);
  else { tab.value = 'weekly'; emit('select', id); }
}
function isoLocal(d: Date) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
let request = 0;
watch([month, tab, () => props.items], async () => {
  if (tab.value !== 'calendar') return;
  const generation = ++request;
  calendarLoading.value = true; calendarError.value = '';
  const y = month.value.getFullYear(), m = month.value.getMonth();
  try {
    const {data} = await api.get('/playlist/calendar', {params: {start_date: isoLocal(new Date(y,m,1)), end_date: isoLocal(new Date(y,m+1,0))}});
    if (generation !== request) return;
    if (data.code !== 0) throw new Error(data.msg);
    events.value = data.data;
  } catch (error) { if (generation === request) { events.value=[]; calendarError.value = error instanceof Error ? error.message : '日历加载失败'; } }
  finally { if (generation === request) calendarLoading.value = false; }
}, {immediate: true});
const byDay = computed(() => {
  const result: Record<string, Event[]> = {};
  for (const event of events.value) {
    const start = new Date(event.start.slice(0,10) + 'T00:00:00');
    const lastDay = event.end
      ? new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Shanghai'}).format(new Date(new Date(event.end).getTime() - 1))
      : event.start.slice(0,10);
    const finish = new Date(lastDay + 'T00:00:00');
    for (const day = new Date(start); day <= finish; day.setDate(day.getDate()+1)) {
      (result[isoLocal(day)] ||= []).push(event);
    }
  }
  return result;
});
</script>
<style scoped>
:deep(.el-calendar-day) { overflow-y: auto; }
</style>
