<script lang="ts">
export interface RemindType {
  id: number;
  label: string;
}
export interface RepeatType {
  id: number;
  label: string;
  tag: string;
}
// 日程提醒类型
export const ReminderOptions: RemindType[] = [
  { id: 0, label: "None" },
  { id: 1, label: "On the day 9:00" },
  { id: 2, label: "1 day early 9:00" },
  { id: 3, label: "2 day early 9:00" },
  { id: 4, label: "3 day early 9:00" },
  { id: 5, label: "4 day early 9:00" },
];
// 日程重复类型
export const RepeatOptions: RepeatType[] = [
  { id: 0, label: "None", tag: "" },
  { id: 1, label: "Daily", tag: "day" },
  { id: 2, label: "Weekly", tag: "week" },
  { id: 3, label: "Monthly", tag: "month" },
  { id: 4, label: "Yearly", tag: "year" },
];
</script>
