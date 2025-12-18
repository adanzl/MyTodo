import { getSave } from "../../js/net_util.js";
import { UserData, S_TS } from "../../js/user_data.js";

const { ref } = window.Vue;
const { ElMessage } = window.ElementPlus;

const Info = {
  setup() {
    const refData = {
      userRadio: ref("userRadio"),
      scheduleList: ref([
        {
          id: 1,
          name: "灿灿日程",
        },
        {
          id: 2,
          name: "昭昭日程",
        },
      ]),
      userData: ref(new UserData()),
    };
    const onUserChange = async (item) => {
      console.log("onUserChange", item);
      try {
        const uData = await getSave(item.id);
        console.log("getSave", uData);
        refData.userData.value = uData;
      } catch (err) {
        console.error(err);
        ElMessage.error(JSON.stringify(err)); // 使用 ElMessage 显示错误
      }
    };

    return {
      message: "欢迎来到Info",
      count: 0,
      ...refData,
      onUserChange,
      S_TS,
    };
  },
  template: `
    <div class='m-4 '>
        <h1>选择用户</h1>
        <el-radio-group v-model="userRadio" size="large" class="mt-4" @change="onUserChange(userRadio)">
            <el-radio-button v-for='item in scheduleList' :key='item.id' :value='item'> {{ item.name }}</el-radio-button>
        </el-radio-group>
        <el-collapse>
            <el-collapse-item v-for='item in userData.schedules' :key='item.id' :title='"["+ item.id + "]" + item.title'>
                <p>
                    range:
                    {{ item?.startTs?.format("YYYY-MM-DD") }} -
                    {{ item?.endTs?.format("YYYY-MM-DD") }}
                    allDay:{{ item.allDay }} order:{{ item.order }}
                </p>
                <p>
                Remind: {{ item.reminder }} | Repeat: {{ item.repeat }} | RepeatEnd:
                {{ S_TS(item.repeatEndTs) }}
                </p>
                <p v-for="(task, idx) in item.subtasks" :key="idx">
                [{{ task.id }}]{{ task.name }}
                </p>
            </el-collapse-item>
        </el-collapse>
    </div>
  `,
  async mounted() {
    console.log("Info组件已挂载");
  },
};
export default Info;
