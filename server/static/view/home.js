import { getUserList } from "../js/net_util.js";
const { ref } = window.Vue;

const Home = {
  setup() {
    const refData = {
      userList: ref([]),
    };
    return {
      ...refData,
    };
  },
  data() {
    return {
      message: "欢迎来到首页",
      count: 0,
    };
  },
  methods: {
    increment() {
      this.count++;
    },
  },
  template: `
    <div class="m-8">
      <el-table :data="userList" stripe style="width: 90%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="Icon" width="80" >
          <template #default="scope">
            <el-avatar :src="scope.row.icon" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="Name" width="100" />
        <el-table-column prop="admin" label="Admin" width="180" />
        <el-table-column prop="score" label="Score" />
      </el-table>
    </div>
  `,
  async mounted() {
    const data = await getUserList();
    console.log("getUserList", data.data);
    Object.assign(this.userList, data.data); // 浅合并
    console.log("Home组件已挂载");
  },
};

export default Home;
