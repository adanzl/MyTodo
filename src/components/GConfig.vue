<script setup lang="ts">
import { ref } from "vue";
defineProps({
  opt_name: String,
});
const configData = ref({
  // 初始化配置数据...
  value: "hello",
});
defineExpose({
  init() {
    console.log("GConfig exposed", configData.value);
  },
});
</script>
