import { getSave } from "@/modal/NetUtil";
import { getColorOptions } from "@/modal/ScheduleType";
import { S_TS, UserData } from "@/modal/UserData";
import { IonRefresher, IonRefresherContent } from "@ionic/vue";
import dayjs from "dayjs";
import { defineComponent, onMounted, ref } from "vue";

export default defineComponent({
  setup() {
    const userData = ref<UserData>(new UserData());
    const toastData = ref({
      isOpen: false,
      duration: 3000,
      text: "",
    });
    onMounted(() => {
      // 获取数据
      getSave(1)
        .then((res: any) => {
          userData.value = JSON.parse(res.data);
          for (let i = 0; i < userData.value.schedules.length; i++) {
            const schedule = userData.value.schedules[i];
            schedule.startTs = dayjs(schedule.startTs);
            schedule.endTs = dayjs(schedule.endTs);
            if (schedule.repeatEndTs) {
              schedule.repeatEndTs = dayjs(schedule.repeatEndTs);
            }
          }
        })
        .catch((err) => {
          toastData.value.isOpen = true;
          toastData.value.text = JSON.stringify(err);
        });
    });
    return {
      userData,
      toastData,
      dayjs,
      S_TS,
      getColorOptions,
    };
  },
  components: {
    IonRefresher,
    IonRefresherContent,
    S_TS,
  },
  data() {
    return {};
  },
  methods: {
    // 刷新页面事件
    handleRefresh(event: any) {
      getSave(1)
        .then((res: any) => {
          this.userData = JSON.parse(res.data);
          for (let i = 0; i < this.userData.schedules.length; i++) {
            const schedule = this.userData.schedules[i];
            schedule.startTs = dayjs(schedule.startTs);
            schedule.endTs = dayjs(schedule.endTs);
            if (schedule.repeatEndTs) {
              schedule.repeatEndTs = dayjs(schedule.repeatEndTs);
            }
          }
          event.target.complete();
        })
        .catch((err) => {
          console.log("handleRefresh", err);
          this.toastData.isOpen = true;
          this.toastData.text = JSON.stringify(err);
          event.target.complete();
        });
    },
  },
});
