<template>
  <div class="checkin-success-page">
    <div class="success-content">
      <div class="success-icon">✅</div>
      <h1 class="success-title">打卡成功</h1>
      <p class="success-message">恭喜你完成本次阅读任务！</p>
      <el-button type="primary" size="large" @click="goToTaskList">
        返回任务列表
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goToTaskList = () => {
  router.push('/daily-tasks')
}
</script>

<style scoped>
.checkin-success-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #f5f7fa;
}

.success-content {
  text-align: center;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.success-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.success-title {
  margin: 0 0 15px 0;
  font-size: 32px;
  font-weight: bold;
  color: #f56c6c;
}

.success-message {
  margin: 0 0 30px 0;
  font-size: 16px;
  color: #606266;
}
</style>
