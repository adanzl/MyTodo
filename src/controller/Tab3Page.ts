import icons from "@/modal/Icons";
import { getSave } from "@/utils/NetUtil";
import { getColorOptions, getGroupOptions, getPriorityOptions } from "@/modal/ScheduleType";
import { S_TS, UserData, UData } from "@/modal/UserData";
import { Icon } from "@iconify/vue";
import { IonRefresher, IonRefresherContent } from "@ionic/vue";
import dayjs from "dayjs";
import { defineComponent, onMounted, ref } from "vue";

export default defineComponent({
  components: {
    IonRefresher,
    IonRefresherContent,
    S_TS,
    Icon,
  },
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
          userData.value = UData.parseUserData(res);
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
      getPriorityOptions,
      getGroupOptions,
      icons,
    };
  },

  data() {
    return {};
  },
  methods: {
    // 刷新页面事件
    handleRefresh(event: any) {
      getSave(1)
        .then((res: any) => {
          this.userData = UData.parseUserData(res);
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
