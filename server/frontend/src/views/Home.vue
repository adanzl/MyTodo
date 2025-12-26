<template>
  <div class="">
    <el-table :data="userList" stripe class="w-full" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="Icon" width="100">
        <template #default="scope">
          <el-avatar :src="scope.row.icon" />
        </template>
      </el-table-column>
      <el-table-column prop="name" label="Name" width="100" />
      <el-table-column prop="admin" label="Admin" width="100" class="items-center text-center" />
      <el-table-column label="WProgress" width="120" class="items-center text-center">
        <template #default="{ row }">
          <el-progress :text-inside="true" :stroke-width="26" :percentage="row.wish_progress" />
        </template>
      </el-table-column>
      <el-table-column prop="wish_list" label="WList" width="100" class="items-center text-center">
      </el-table-column>
      <el-table-column prop="score" label="Score" width="100">
        <template #default="{ row }">
          <el-input v-model="row.score" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="Operations">
        <template #default="{ row }">
          <el-button class="w-16" @click="handleUpdateUser(row)" type="primary"> Update </el-button>
          <el-button class="w-16" @click="onAddScoreBtnClick(row)"> Score </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog
      v-model="dialogForm.visible"
      title="Change Score"
      width="600"
      :before-close="handleDialogClose"
    >
      <span>输入的积分会作用在当前积分上，输入负数则会减少积分</span>
      <div>{{ dialogForm.data.name }} 当前积分: {{ dialogForm.data.score }}</div>
      <div class="flex mt-4">
        <el-input v-model="dialogForm.value" style="width: 240px" placeholder="Please input" />

        <el-button @click="handleAddScore()" class="ml-2 w-16" type="primary"> Submit </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { getList } from "@/api/common";
import { setUserInfo, addScore } from "@/api/user";

const userList = ref<any[]>([]);
const dialogForm = ref({
  visible: false,
  data: null as any,
  value: 0,
});
const loading = ref(false);

const refreshUserList = async () => {
  loading.value = true;
  try {
    const response = await getList("t_user");
    if (response && response.data) {
      // API 返回的是分页格式，用户数组在 response.data.data 中
      const users = response.data.data || response.data;
      userList.value = Array.isArray(users) ? users : [];
    } else {
      userList.value = [];
    }
  } catch (error) {
    console.error("获取用户列表失败:", error);
    ElMessage.error("获取用户列表失败");
  } finally {
    loading.value = false;
  }
};

const handleUpdateUser = async (item: any) => {
  try {
    const data = {
      id: item.id,
      score: item.score,
    };
    await setUserInfo(data.id, data.score);
    console.log("update user", data);
    await refreshUserList();
  } catch (error) {
    console.error("更新用户失败:", error);
    ElMessage.error("更新用户失败");
  }
};

const onAddScoreBtnClick = (item: any) => {
  dialogForm.value.visible = true;
  dialogForm.value.data = item;
};

const handleAddScore = async () => {
  try {
    await addScore(dialogForm.value.data.id, "pcAdmin", dialogForm.value.value, "管理后台变更");
    await refreshUserList();
    dialogForm.value.visible = false;
    dialogForm.value.value = 0;
  } catch (error) {
    console.error("添加积分失败:", error);
    ElMessage.error("添加积分失败");
  }
};

const handleDialogClose = () => {
  dialogForm.value.visible = false;
  dialogForm.value.value = 0;
};

onMounted(async () => {
  await refreshUserList();
});
</script>

<style scoped></style>
