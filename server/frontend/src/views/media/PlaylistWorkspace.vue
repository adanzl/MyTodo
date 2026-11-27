<template>
  <el-tabs v-model="tab">
    <el-tab-pane label="Weekly" name="weekly">
      <slot v-if="tab === 'weekly'" :calendar="false" :draft="null" :saving="saving" :save="saveDraft"
        :create="createCalendar" :menu="calendarMenu" />
    </el-tab-pane>
    <el-tab-pane label="播放列表" name="calendar-list">
      <slot v-if="tab === 'calendar-list'" :calendar="true" :draft="draft" :saving="saving" :save="saveDraft"
        :create="createCalendar" :menu="calendarMenu" />
    </el-tab-pane>
    <el-tab-pane label="播放日历" name="calendar">
      <section class="playlist-calendar">
        <div class="calendar-toolbar">
          <div class="calendar-controls">
            <el-date-picker v-model="month" type="month" format="YYYY年MM月" :clearable="false"
              size="small" class="calendar-month-picker" aria-label="选择月份" />
            <el-button-group size="small">
              <el-button :icon="ArrowLeft" title="上个月" aria-label="上个月" @click="changeMonth(-1)" />
              <el-button @click="goToday">今天</el-button>
              <el-button :icon="ArrowRight" title="下个月" aria-label="下个月" @click="changeMonth(1)" />
            </el-button-group>
            <el-button type="primary" size="small" :icon="Refresh" :loading="calendarLoading || refreshing"
              title="刷新日历" aria-label="刷新日历" @click="loadCalendar()" />
          </div>
          <div class="calendar-filters">
            <el-select v-model="modeFilter" size="small" class="calendar-mode-filter" aria-label="排期类型">
              <el-option label="全部类型" value="all" />
              <el-option label="Weekly" value="weekly" />
              <el-option label="日期排期" value="calendar" />
            </el-select>
            <el-select v-model="deviceFilter" size="small" clearable filterable placeholder="全部设备"
              class="calendar-device-filter" aria-label="筛选设备">
              <el-option v-for="device in calendarDevices" :key="device.key" :label="device.label" :value="device.key" />
            </el-select>
          </div>
        </div>
        <div class="calendar-legend">
          <span><i class="calendar-dot weekly" />Weekly</span>
          <span><i class="calendar-dot dated" />日期排期</span>
          <span class="calendar-summary">{{ monthSummary }}</span>
          <span class="calendar-hint">点击日期查看明细，按日期范围和启动时间展示</span>
        </div>
        <el-alert v-if="calendarError" :title="calendarError" type="error" show-icon :closable="false" />
        <div class="calendar-layout">
          <el-calendar v-model="month" class="schedule-calendar">
            <template #header><span>{{ monthLabel }}</span></template>
            <template #date-cell="{data}">
              <div class="calendar-cell" :data-date="data.day" :class="{'is-outside': data.type !== 'current-month'}">
                <div class="calendar-day-header">
                  <span class="calendar-day-number" :class="{'is-today': data.day === todayKey}">{{ Number(data.day.slice(-2)) }}</span>
                  <span v-if="byDay[data.day]?.length" class="calendar-day-count">{{ byDay[data.day].length }}项</span>
                </div>
                <div class="calendar-day-events">
                  <button v-for="event in (byDay[data.day] || []).slice(0, 3)" :key="eventKey(event)"
                    type="button" class="calendar-event" :class="event.mode === 'weekly' ? 'weekly' : 'dated'"
                    :title="eventTooltip(event)" :aria-label="eventTooltip(event)" @click.stop="selectDay(data.day)">
                    <span class="calendar-event-time">{{ event.start.slice(0,10) < data.day ? '续播' : event.start.slice(11,16) }}</span>
                    <span class="calendar-event-name">{{ event.name }}</span>
                    <span v-if="event.occurrence_count > 1" class="calendar-event-count">×{{ formatCount(event.occurrence_count) }}</span>
                  </button>
                  <button v-if="(byDay[data.day]?.length || 0) > 3" type="button" class="calendar-more"
                    @click.stop="selectDay(data.day)">还有 {{ byDay[data.day].length - 3 }} 项</button>
                </div>
              </div>
            </template>
          </el-calendar>
          <aside class="calendar-agenda">
            <div class="calendar-agenda-header">
              <div class="calendar-agenda-date">{{ selectedDateLabel }}</div>
              <span class="calendar-agenda-count">{{ selectedEvents.length }} 项排期</span>
            </div>
            <div v-if="calendarLoading && !events.length" class="calendar-agenda-loading">正在加载排期…</div>
            <el-empty v-else-if="!selectedEvents.length" description="当天暂无排期" :image-size="64" />
            <div v-else class="calendar-agenda-list">
              <article v-for="event in selectedEvents" :key="eventKey(event)" class="calendar-agenda-item"
                :class="event.mode === 'weekly' ? 'weekly' : 'dated'">
                <div class="calendar-agenda-top">
                  <span class="calendar-mode-tag">{{ event.mode === 'weekly' ? 'Weekly' : '日期排期' }}</span>
                  <span v-if="event.start.slice(0,10) < selectedDay" class="calendar-continuation">跨日续播</span>
                  <span v-else-if="event.end && shanghaiDay(new Date(new Date(event.end).getTime() - 1)) > selectedDay" class="calendar-continuation">跨日</span>
                </div>
                <div class="calendar-agenda-name">{{ event.name }}</div>
                <dl class="calendar-event-details">
                  <div><dt>{{ event.occurrence_count > 1 ? '触发时段' : '时间' }}</dt><dd>{{ eventTimeRange(event) }}</dd></div>
                  <div v-if="event.occurrence_count > 1"><dt>触发次数</dt><dd>{{ formatCount(event.occurrence_count) }} 次</dd></div>
                  <div><dt>设备</dt><dd>{{ deviceLabel(event) }}</dd></div>
                  <div><dt>{{ event.occurrence_count > 1 ? '单次时长' : '时长' }}</dt><dd>{{ durationLabel(event.length_seconds) }}</dd></div>
                </dl>
                <el-button link type="primary" size="small" @click="selectEvent(event.id)">编辑</el-button>
              </article>
            </div>
          </aside>
        </div>
      </section>
    </el-tab-pane>
  </el-tabs>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { ArrowLeft, ArrowRight, Refresh } from '@element-plus/icons-vue';
import { api } from '@/api/config';
import { deletePlaylist, getPlaylist, updatePlaylist } from '@/api/api-playlist';
import { createPlaylistId } from '@/utils/playlist';
import type { Playlist } from '@/types/playlist';
interface Event {
  id: string; name: string; mode: string; start: string; end: string | null;
  occurrence_count: number; last_start?: string; device_key?: string | null; length_seconds?: number | null; device?: Playlist['device'];
}
const props = defineProps<{items: Playlist[]; activeId: string; refreshing?: boolean}>();
const emit = defineEmits<{select: [id: string]; saved: []; refresh: []; viewChange: [view: string]; open: [row: Playlist]}>();
const tab = ref('weekly'), saving = ref(false), calendarLoading = ref(false), calendarError = ref('');
watch(tab, view => emit('viewChange', view), {immediate: true});
const todayKey = shanghaiDay(new Date());
const month = ref(new Date(todayKey + 'T12:00:00')), events = ref<Event[]>([]), draft = ref<Playlist | null>(null);
const modeFilter = ref('all'), deviceFilter = ref('');
const monthKey = computed(() => isoLocal(month.value).slice(0,7));
const monthLabel = computed(() => `${month.value.getFullYear()}年${month.value.getMonth()+1}月`);
const selectedDay = computed(() => isoLocal(month.value));
const selectedDateLabel = computed(() => new Intl.DateTimeFormat('zh-CN', {month: 'long', day: 'numeric', weekday: 'long'}).format(month.value));
const playlistById = computed(() => new Map(props.items.map(row => [row.id, row])));
const calendarConfigKey = computed(() => props.items.map(row => [row.id, row._revision, row.status].join(':')).join('|'));
const calendarRange = computed(() => {
  const first = new Date(month.value.getFullYear(), month.value.getMonth(), 1, 12);
  const last = new Date(month.value.getFullYear(), month.value.getMonth()+1, 0, 12);
  first.setDate(first.getDate()-6); last.setDate(last.getDate()+6);
  return {start: isoLocal(first), end: isoLocal(last)};
});
const lastWeeklyId = ref(''), lastCalendarId = ref(''), pendingCalendarId = ref(''), draftBaseline = ref('');
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
  lastCalendarId.value = row.id;
  if (draft.value?.id !== row.id) { resetDraft(row); return; }
  if (JSON.stringify(scheduleFields(draft.value)) === draftBaseline.value) resetDraft(row);
  else if (JSON.stringify(scheduleFields(row)) === draftBaseline.value) draft.value._revision = row._revision;
}, {immediate: true});
watch([tab, weeklyItems, calendarItems, () => props.activeId], () => {
  if (tab.value === 'weekly') {
    if (!weeklyItems.value.some(row => row.id === props.activeId)) {
      const row = weeklyItems.value.find(row => row.id === lastWeeklyId.value) || weeklyItems.value[0];
      if (row) emit('select', row.id);
    }
  } else if (tab.value === 'calendar-list') {
    if (pendingCalendarId.value && !calendarItems.value.some(row => row.id === pendingCalendarId.value)) return;
    const row = calendarItems.value.find(row => row.id === pendingCalendarId.value) ||
      calendarItems.value.find(row => row.id === props.activeId) ||
      calendarItems.value.find(row => row.id === lastCalendarId.value) || calendarItems.value[0];
    if (!row) { draft.value = null; return; }
    pendingCalendarId.value = '';
    if (draft.value?.id !== row.id) resetDraft(row);
    if (props.activeId !== row.id) emit('select', row.id);
  }
}, {immediate: true});
function edit(row: Playlist) {
  tab.value = 'calendar-list';
  pendingCalendarId.value = row.id;
  if (props.items.some(item => item.id === row.id)) {
    resetDraft(row);
    emit('select', row.id);
  }
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
async function createCalendar(source?: Playlist, requestedName?: string) {
  saving.value = true;
  try {
    const today = isoLocal(new Date()), id = createPlaylistId();
    const suffix = String(Math.floor(Math.random() * 1000000)).padStart(6, '0');
    const name = requestedName?.trim() || `日期播放列表-${suffix}`;
    const seed: Partial<Playlist> = source ? JSON.parse(JSON.stringify(source)) : {};
    delete seed._revision;
    const response = await updatePlaylist({...seed, id, name, mode: 'calendar', status: 0, isPlaying: false, current_index: 0,
      start_date: seed.start_date || today, end_date: seed.end_date || today, start_time: seed.start_time || '09:00:00',
      pre_list: seed.pre_list || [], playlist: seed.playlist || [], pre_lists: seed.pre_lists || Array.from({length: 7}, () => []),
      schedule: {...seed.schedule, enabled: 0, duration: seed.schedule?.duration || 0, cron: seed.schedule?.cron || ''}});
    if (response.code !== 0) throw new Error(response.msg);
    const refreshed = await getPlaylist(id);
    if (refreshed.code !== 0) throw new Error(refreshed.msg);
    const row = (refreshed.data as Record<string, Playlist>)[id];
    pendingCalendarId.value = id;
    emit('saved');
    if (tab.value === 'calendar-list') edit(row);
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '创建失败'); }
  finally { saving.value = false; }
}
async function calendarMenu(command: string, id: string) {
  const row = calendarItems.value.find(item => item.id === id);
  if (!row) return;
  if (command === 'delete') { await removeCalendar(row); return; }
  if (command !== 'copy') return;
  try {
    const suffix = String(Math.floor(Math.random() * 1000000)).padStart(6, '0');
    const {value} = await ElMessageBox.prompt('请输入播放列表名称', '复制播放列表', {
      inputValue: `${row.name}_副本-${suffix}`,
      inputValidator: (value: string) => !!value.trim() || '名称不能为空',
      confirmButtonText: '确定', cancelButtonText: '取消',
    });
    await createCalendar(row, value);
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '复制失败');
  }
}
async function removeCalendar(row: Playlist) {
  try { await ElMessageBox.confirm(`删除日期排期「${row.name}」？`, '删除排期', {type: 'warning'}); }
  catch { return; }
  saving.value = true;
  try {
    const saved = await deletePlaylist(row.id, row._revision);
    if (saved.code !== 0) throw new Error(saved.msg);
    if (draft.value?.id === row.id) draft.value = null;
    if (lastCalendarId.value === row.id) lastCalendarId.value = '';
    if (pendingCalendarId.value === row.id) pendingCalendarId.value = '';
    emit('saved');
    ElMessage.success('已删除');
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '删除失败'); }
  finally { saving.value = false; }
}
function saveDraft() { if (draft.value) return submit(draft.value); }
async function selectEvent(id: string) {
  try {
    const response = await getPlaylist(id);
    if (response.code !== 0) throw new Error(response.msg || '读取播放列表失败');
    const row = (response.data as Record<string, Playlist> | undefined)?.[id];
    if (!row) throw new Error('播放列表已不存在，请刷新日历');
    emit('open', row);
    if (row.mode === 'calendar') edit(row);
    else { lastWeeklyId.value = id; tab.value = 'weekly'; emit('select', id); }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取播放列表失败');
  }
}
function isoLocal(d: Date) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function shanghaiDay(value: Date) {
  return new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Shanghai'}).format(value);
}
function selectDay(day: string) { month.value = new Date(day + 'T12:00:00'); }
function changeMonth(offset: number) {
  const current = month.value;
  const target = new Date(current.getFullYear(), current.getMonth()+offset, 1, 12);
  const last = new Date(target.getFullYear(), target.getMonth()+1, 0).getDate();
  target.setDate(Math.min(current.getDate(), last));
  month.value = target;
}
function goToday() { selectDay(shanghaiDay(new Date())); }
function eventKey(event: Event) { return `${event.id}:${event.start}`; }
function eventDeviceKey(event: Event) { return event.device_key || '__no_device__'; }
function deviceLabel(event: Event) {
  const row = playlistById.value.get(event.id);
  return event.device?.name || event.device?.address || row?.device?.name || row?.device?.address || '未设置设备';
}
function clock(value: string) {
  const time = value.slice(11,19);
  return time.endsWith(':00') ? time.slice(0,5) : time;
}
function eventTimeRange(event: Event) {
  const end = event.occurrence_count > 1 ? event.last_start || event.start : event.end;
  if (!end) return `${clock(event.start)} 开始`;
  if (event.start.slice(0,10) === end.slice(0,10)) return `${clock(event.start)} – ${clock(end)}`;
  return `${event.start.slice(5,10)} ${clock(event.start)} – ${end.slice(5,10)} ${clock(end)}`;
}
function durationLabel(seconds: number | null | undefined) {
  if (seconds == null || !Number.isFinite(seconds)) return '待补齐';
  const value = Math.round(seconds), hours = Math.floor(value/3600), minutes = Math.floor(value%3600/60), rest = value%60;
  return [hours ? `${hours}小时` : '', minutes ? `${minutes}分` : '', rest ? `${rest}秒` : ''].filter(Boolean).join('') || '0秒';
}
function formatCount(value: number) { return value.toLocaleString('zh-CN'); }
function eventTooltip(event: Event) {
  const count = event.occurrence_count > 1 ? ` · ${formatCount(event.occurrence_count)} 次触发` : '';
  return `${event.name}\n${eventTimeRange(event)}${count}\n${deviceLabel(event)}`;
}
const calendarDevices = computed(() => {
  const options = new Map<string, string>();
  for (const row of props.items) {
    const kind = row.device?.type || 'dlna';
    const identity = kind === 'mi' ? row.device?.did : row.device?.address;
    const key = identity?.trim() ? JSON.stringify([kind, identity.trim()]) : '__no_device__';
    options.set(key, row.device?.name || row.device?.address || '未设置设备');
  }
  for (const event of events.value) options.set(eventDeviceKey(event), deviceLabel(event));
  return [...options].map(([key,label]) => ({key,label})).sort((a,b) => a.label.localeCompare(b.label,'zh-CN'));
});
watch(calendarDevices, options => {
  if (deviceFilter.value && !options.some(option => option.key === deviceFilter.value)) deviceFilter.value = '';
});
const filteredEvents = computed(() => events.value.filter(event =>
  (modeFilter.value === 'all' || event.mode === modeFilter.value) &&
  (!deviceFilter.value || eventDeviceKey(event) === deviceFilter.value)
));
let request = 0;
let loadedMonth = '';
async function loadCalendar() {
  const generation = ++request, key = monthKey.value;
  calendarLoading.value = true; calendarError.value = '';
  if (loadedMonth !== key) { events.value = []; loadedMonth = ''; }
  const range = calendarRange.value;
  try {
    const {data} = await api.get('/playlist/calendar', {params: {start_date: range.start, end_date: range.end}});
    if (data.code !== 0) throw new Error(data.msg || '日历加载失败');
    if (!Array.isArray(data.data)) throw new Error('日历数据格式错误');
    if (generation !== request) return;
    events.value = data.data as Event[];
    loadedMonth = key;
  } catch (error) {
    if (generation === request) {
      const message = error instanceof Error ? error.message : '日历加载失败';
      if (loadedMonth === key) calendarError.value = `刷新失败，保留上次数据：${message}`;
      else { events.value=[]; calendarError.value = message; }
    }
  } finally {
    if (generation === request) { calendarLoading.value = false; }
  }
}
async function refreshCalendar() {
  if (tab.value === 'calendar' && !calendarLoading.value) await loadCalendar();
}
defineExpose({refreshCalendar});
watch([monthKey, tab, calendarConfigKey], () => {
  if (tab.value === 'calendar') void loadCalendar();
  else { ++request; calendarLoading.value = false; }
}, {immediate: true});
const byDay = computed(() => {
  const result: Record<string, Event[]> = {};
  const range = calendarRange.value;
  for (const event of filteredEvents.value) {
    const first = event.start.slice(0,10);
    const last = event.end ? shanghaiDay(new Date(new Date(event.end).getTime()-1)) : first;
    const start = first < range.start ? range.start : first;
    const end = last > range.end ? range.end : last;
    for (const day = new Date(start + 'T12:00:00'); isoLocal(day) <= end; day.setDate(day.getDate()+1)) {
      (result[isoLocal(day)] ||= []).push(event);
    }
  }
  return result;
});
const selectedEvents = computed(() => byDay.value[selectedDay.value] || []);
const monthSummary = computed(() => {
  const days = Object.entries(byDay.value).filter(([day]) => day.startsWith(monthKey.value));
  const lists = new Set(days.flatMap(([,items]) => items.map(event => event.id)));
  return `本月 ${lists.size} 条列表 · ${days.length} 天有排期`;
});
</script>
<style scoped>
.playlist-calendar { min-width: 0; }
.calendar-toolbar, .calendar-controls, .calendar-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.calendar-toolbar { justify-content: space-between; margin-bottom: 10px; }
.calendar-controls :deep(.calendar-month-picker) { width: 148px !important; }
.calendar-mode-filter { width: 116px; }
.calendar-device-filter { width: 180px; }
.calendar-legend { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 10px; color: var(--el-text-color-secondary); font-size: 12px; }
.calendar-legend > span { display: inline-flex; align-items: center; gap: 5px; }
.calendar-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; }
.calendar-dot.weekly { background: var(--el-color-primary); }
.calendar-dot.dated { background: var(--el-color-success); }
.calendar-summary { color: var(--el-text-color-regular); }
.calendar-hint { margin-left: auto; }
.calendar-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 12px; align-items: start; }
.schedule-calendar { min-width: 0; border: 1px solid var(--el-border-color-lighter); border-radius: 6px; overflow: hidden; }
.schedule-calendar :deep(.el-calendar__header) { display: none; }
.schedule-calendar :deep(.el-calendar__body) { padding: 0; }
.schedule-calendar :deep(.el-calendar-table thead th) { padding: 9px 0; font-size: 12px; color: var(--el-text-color-secondary); }
.schedule-calendar :deep(.el-calendar-table .el-calendar-day) { height: 140px; padding: 6px; overflow: hidden; }
.schedule-calendar :deep(.el-calendar-table td.is-selected) { background: var(--el-color-primary-light-8); }
.schedule-calendar :deep(.el-calendar-table td.is-selected .el-calendar-day) { background: var(--el-color-primary-light-8); box-shadow: inset 0 0 0 2px var(--el-color-primary); }
.schedule-calendar :deep(.el-calendar-table td.is-selected .calendar-day-number) { background: var(--el-color-primary-dark-2); color: var(--el-color-white); font-weight: 700; }
.schedule-calendar :deep(.el-calendar-table td.is-selected .calendar-day-count) { color: var(--el-color-primary-dark-2); font-weight: 600; }
.calendar-cell { min-width: 0; height: 100%; }
.calendar-day-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; height: 22px; }
.calendar-day-number { display: inline-flex; width: 22px; height: 22px; align-items: center; justify-content: center; font-size: 12px; border-radius: 50%; }
.calendar-day-number.is-today { color: white; background: var(--el-color-primary); font-weight: 600; }
.calendar-day-count { font-size: 10px; color: var(--el-text-color-secondary); }
.calendar-cell.is-outside .calendar-day-header { opacity: .45; }
.calendar-cell.is-outside .calendar-day-events { opacity: .65; }
.calendar-day-events { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.calendar-event { display: flex; align-items: center; gap: 4px; width: 100%; min-width: 0; border: 0; border-left: 3px solid; border-radius: 3px; padding: 3px 5px; cursor: pointer; text-align: left; font: inherit; font-size: 11px; line-height: 16px; }
.calendar-event.weekly { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); color: var(--el-color-primary-dark-2); }
.calendar-event.dated { border-color: var(--el-color-success); background: var(--el-color-success-light-9); color: var(--el-color-success-dark-2); }
.calendar-event:hover { filter: brightness(.96); }
.calendar-event-time { flex: none; font-variant-numeric: tabular-nums; font-size: 10px; }
.calendar-event-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.calendar-event-count { flex: none; font-size: 9px; }
.calendar-more { padding: 0 3px; border: 0; background: transparent; text-align: left; font-size: 11px; line-height: 16px; color: var(--el-color-primary); cursor: pointer; }
.calendar-event:focus-visible, .calendar-more:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 1px; }
.calendar-agenda { min-width: 0; max-height: calc(100vh - 240px); overflow-y: auto; border: 1px solid var(--el-border-color-lighter); border-radius: 6px; background: var(--el-bg-color); }
.calendar-agenda-header { position: sticky; top: 0; z-index: 1; display: flex; align-items: baseline; justify-content: space-between; gap: 8px; padding: 13px 14px; border-bottom: 1px solid var(--el-border-color-lighter); background: var(--el-bg-color); }
.calendar-agenda-date { font-size: 14px; font-weight: 600; color: var(--el-text-color-primary); }
.calendar-agenda-count { flex: none; color: var(--el-text-color-secondary); font-size: 11px; }
.calendar-agenda-loading { padding: 32px 16px; color: var(--el-text-color-secondary); text-align: center; font-size: 12px; }
.calendar-agenda-list { padding: 0 14px; }
.calendar-agenda-item { padding: 13px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.calendar-agenda-item:last-child { border-bottom: 0; }
.calendar-agenda-top { display: flex; align-items: center; gap: 7px; margin-bottom: 6px; }
.calendar-mode-tag { padding: 1px 6px; border-radius: 3px; font-size: 10px; line-height: 18px; }
.calendar-agenda-item.weekly .calendar-mode-tag { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.calendar-agenda-item.dated .calendar-mode-tag { background: var(--el-color-success-light-9); color: var(--el-color-success); }
.calendar-continuation { font-size: 10px; color: var(--el-color-warning-dark-2); }
.calendar-agenda-name { font-size: 13px; font-weight: 500; line-height: 20px; overflow-wrap: anywhere; color: var(--el-text-color-primary); }
.calendar-event-details { margin: 7px 0 5px; font-size: 11px; line-height: 19px; }
.calendar-event-details > div { display: grid; grid-template-columns: 54px minmax(0, 1fr); gap: 6px; margin-bottom: 2px; }
.calendar-event-details dt { color: var(--el-text-color-secondary); }
.calendar-event-details dd { margin: 0; overflow-wrap: anywhere; color: var(--el-text-color-regular); }
@media (max-width: 1100px) {
  .calendar-layout { grid-template-columns: minmax(0, 1fr); }
  .calendar-agenda { max-height: none; }
  .calendar-hint { margin-left: 0; }
}
@media (max-width: 600px) {
  .schedule-calendar :deep(.el-calendar-table .el-calendar-day) { height: 136px; padding: 4px; }
  .calendar-event { gap: 2px; padding: 3px 2px; }
  .calendar-event-time { display: none; }
  .calendar-event-count { display: none; }
  .calendar-device-filter { width: 156px; }
}
</style>
