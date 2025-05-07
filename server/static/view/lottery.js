import { getData, getList, setData } from "../js/net_util.js";

const { ref } = window.Vue;
const { ElMessage } = window.ElementPlus;
const Lottery = {
  setup() {
    const refData = {
      lotteryData: ref([]),
    };
    const handleEdit = (index, row) => {
      console.log(index, row);
    };
    const handleDelete = (index, row) => {
      console.log(index, row);
    };
    return {
      ...refData,
      handleEdit,
      handleDelete,
    };
  },
  async mounted() {
    console.log("Lottery组件已挂载");
    getList("t_gift_category")
      .then((data) => {
        const d = data.data;
        console.log(d);
        Object.assign(this.lotteryData, d); // 浅合并
      })
      .catch((err) => {
        console.error(err);
        ElMessage.error(JSON.stringify(err));
      });
  },
  data() {
    return {
      message: "欢迎来到Lottery",
    };
  },
  methods: {
    increment() {},
  },
  template: `
    <div class="m-8">
        <el-table :data="lotteryData" style="width: 100%">
          <el-table-column label="Img" width="80" >
            <template #default="scope">
              <el-avatar :src="scope.row.img" />
            </template>
          </el-table-column>
          <el-table-column prop="name" label="Name" width="100" />
          <el-table-column prop="weight" label="Weight" width="180" />
          <el-table-column label="Operations" >
            <template #default="scope">
              <el-button size="small" @click="handleEdit(scope.$index, scope.row)">
                Edit
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="handleDelete(scope.$index, scope.row)"
              >
                Delete
              </el-button>
            </template>
          </el-table-column>
        </el-table>
    </div>
  `,
};

export default Lottery;
