import { getData, getList, setData } from "../js/net_util.js";

const { ref } = window.Vue;
const { ElMessage } = window.ElementPlus;
const Lottery = {
  setup() {
    const refData = {
      selectedCate: ref(),
      modifyCateModel: ref(false),
      lotteryData: ref([]),
      lotteryCatList: ref([]),
    };
    const handleEdit = (index, row) => {
      console.log(index, row);
    };
    const handleDelete = (index, row) => {
      console.log(index, row);
    };
    const onCateChange = (item) => {
      console.log(item);
    };
    return {
      ...refData,
      handleEdit,
      handleDelete,
      onCateChange,
    };
  },
  async mounted() {
    console.log("Lottery组件已挂载");
    getList("t_gift_category")
      .then((data) => {
        const d = data.data;
        console.log(d);
        Object.assign(this.lotteryCatList, d); // 浅合并
        this.lotteryCatList.unshift({ id: 0, name: "全部" });
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
    <div class="m-4">
      <div class="flex items-center">
        <el-radio-group size="large" v-model="selectedCate" class="" @change="onCateChange(selectedCate)">
          <el-radio-button v-for='item in lotteryCatList' :key='item.id' :value='item'> {{ item.name }}</el-radio-button>
        </el-radio-group>
        <el-button type="primary" class="ml-1" @click="modifyCateModel=true"><el-icon><Edit /></el-icon></el-button>
        <div class="flex-1 flex items-center justify-end">
          <el-button type="primary" class="">添加奖品</el-button>
        </div>
      </div>
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
    <el-dialog v-model="modifyCateModel" title="类别管理" width="800" destroy-on-close>
      <el-table :data="lotteryCatList">
        <el-table-column property="id" label="ID" width="150" />
        <el-table-column property="name" label="Name" width="200" />
        <el-table-column  label="OP" />
      </el-table>
      <el-button class="mt-4" style="width: 100%" @click="onAddItem">
        Add Item
      </el-button>
    </el-dialog>
  `,
};

export default Lottery;
