<script lang="ts">
import dayjs from "dayjs";

export interface SubTask {
  id: number;
  name: string;
}

// 日程计划数据
export interface ScheduleData {
  // ===== 日程数据 =====
  id: number; // 任务id
  title: string; // 任务标题
  startTs?: dayjs.Dayjs; // 开始时间
  endTs?: dayjs.Dayjs; // 结束时间
  reminder: number; // 提醒类型
  repeat: number; // 重复类型
  repeatEndTs?: dayjs.Dayjs; // 重复结束类型
  subTasks: SubTask[]; // 子任务列表
}

// 日程存档
export interface ScheduleSave {
  state: number;
  subTasks: Map<number, number>;
}

// 用户数据
export interface UserData {
  id: number | undefined; // 用户id
  name: string; // 用户名称
  schedules: ScheduleData[]; // 日程计划列表
  // 计划完成情况  日期->对应日期完成情况(任务id->完成情况)
  save: Map<string, Map<number, ScheduleSave>>;
}

export const SAVE_TS = (dt: dayjs.Dayjs): string => {
  return dt.format("YYYY-MM-DD");
};
</script>
