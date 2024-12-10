<script lang="ts">
import dayjs from "dayjs";

// 日程计划数据
export type ScheduleData = {
  id: number | undefined; // 任务id
  title: string; // 任务标题
  startTs?: dayjs.Dayjs; // 开始时间
  endTs?: dayjs.Dayjs; // 结束时间
  reminder: number; // 提醒类型
  repeat: number; // 重复类型
  repeatEndTs?: dayjs.Dayjs; // 重复结束类型
};

// 用户数据
export type UserData = {
  id: number | undefined; // 用户id
  name: string; // 用户名称
  schedules: ScheduleData[]; // 日程计划列表
};
</script>
