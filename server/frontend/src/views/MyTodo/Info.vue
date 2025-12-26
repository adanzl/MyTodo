<template>
  <div class="m-4">
    <h1>选择用户</h1>
    <el-radio-group v-model="userRadioId" size="large" class="mt-4" @change="onUserChange">
      <el-radio-button v-for="item in scheduleList" :key="item.id" :value="item.id">
        {{ item.name }}
      </el-radio-button>
    </el-radio-group>
    <el-collapse>
      <el-collapse-item
        v-for="item in userData.schedules"
        :key="item.id"
        :title="'[' + item.id + ']' + item.title"
      >
        <p>
          range: {{ item?.startTs?.format("YYYY-MM-DD") }} -
          {{ item?.endTs?.format("YYYY-MM-DD") }} allDay:{{ item.allDay }} order:{{ item.order }}
        </p>
        <p>
          Remind: {{ item.reminder }} | Repeat: {{ item.repeat }} | RepeatEnd:
          {{ S_TS(item.repeatEndTs) }}
        </p>
        <p v-for="(task, idx) in item.subtasks" :key="idx">[{{ task.id }}]{{ task.name }}</p>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import { getSave } from "@/api/user";
import { UserData } from "@/models";
import { S_TS } from "@/utils/date";

const userRadioId = ref<number>(1);
const scheduleList = ref([
  {
    id: 1,
    name: "灿灿日程",
  },
  {
    id: 2,
    name: "昭昭日程",
  },
]);
const userData = ref(new UserData());

const selectedUser = computed(() => {
  return scheduleList.value.find(item => item.id === userRadioId.value) || scheduleList.value[0];
});

const onUserChange = async () => {
  const item = selectedUser.value;
  console.log("onUserChange", item);
  try {
    const uData = await getSave(item.id);
    console.log("getSave", uData);
    userData.value = uData;
  } catch (err) {
    console.error(err);
    ElMessage.error(JSON.stringify(err));
  }
};

onMounted(() => {
  console.log("Info组件已挂载");
});
</script>

<style scoped></style>
