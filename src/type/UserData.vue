<script lang="ts">
import dayjs from "dayjs";

export interface SubTask {
  id: number;
  name: string;
  state: number;
}

// 日程计划数据
export interface ScheduleData {
  id: number | undefined; // 任务id
  state: number; // 任务状态
  title: string; // 任务标题
  startTs?: dayjs.Dayjs; // 开始时间
  endTs?: dayjs.Dayjs; // 结束时间
  reminder: number; // 提醒类型
  repeat: number; // 重复类型
  repeatEndTs?: dayjs.Dayjs; // 重复结束类型
  subTasks: SubTask[]; // 子任务列表
}

// 用户数据
export interface UserData {
  id: number | undefined; // 用户id
  name: string; // 用户名称
  schedules: ScheduleData[]; // 日程计划列表
}
</script>
