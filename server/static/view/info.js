import { getUserList, getSave } from "../js/net_util.js";
import { UserData, S_TS } from "../js/user_data.js";

const Info = {
  setup() {
    const { ref } = window.Vue;
    const { ElMessage } = window.ElementPlus;
    const userRadio = ref("userRadio");
    const userList = ref([]);
    const userData = ref(new UserData());

    const onUserChange = async (item) => {
      console.log("onUserChange", item);
      try {
        const uData = await getSave(item.id);
        console.log("getSave", uData);
        userData.value = uData;
      } catch (err) {
        console.error(err);
        ElMessage.error(JSON.stringify(err)); // 使用 ElMessage 显示错误
      }
    };

    return {
      message: "欢迎来到Info",
      count: 0,
      userRadio,
      userList,
      userData,
      onUserChange,
      S_TS,
    };
  },
  template: `
    <div class='m-4 '>
        <h1>选择用户</h1>
        <el-radio-group v-model="userRadio" size="large" class="mt-4" @change="onUserChange(userRadio)">
            <el-radio-button v-for='item in userList' :key='item.id' :value='item'> {{ item.name }}</el-radio-button>
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
    const data = await getUserList();
    console.log("getUserList", data.data);
    Object.assign(this.userList, data.data); // 浅合并
  },
};
export default Info;
