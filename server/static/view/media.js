import { bluetoothAction, getRdsData, setRdsData } from "../js/net_util.js";

const { ref, onMounted, nextTick, watch } = window.Vue;
const { ElMessage } = window.ElementPlus;
let component = null;
async function loadTemplate() {
  const timestamp = `?t=${Date.now()}`;
  const response = await fetch(`./view/media-template.html${timestamp}`);
  return await response.text(); // 获取模板内容
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        dialogForm: ref({
          visible: false,
          data: null,
          value: 0,
        }),
        scanDialogVisible: ref(false),
        directoryDialogVisible: ref(false),
        selectedPath: ref(""),
        currentPath: ref("/mnt"),
        directoryList: ref([]),
        directoryLoading: ref(false),
        fileList: ref([]),
        fileListLoading: ref(false),
        cronExpression: ref(""),
        nextRunTime: ref(""),
        cronBuilderVisible: ref(false),
        cronBuilder: ref({
          second: "*",
          secondCustom: "",
          minute: "*",
          minuteCustom: "",
          hour: "*",
          hourCustom: "",
          day: "*",
          dayCustom: "",
          month: "*",
          monthCustom: "",
          weekday: "*",
          weekdayCustom: "",
          generated: "",
        }),
        cronPreviewVisible: ref(false),
        cronPreviewTimes: ref([]),
        loading: ref(false),
        deviceList: ref([]),
        connectedDeviceList: ref([]),
      };

      // 刷新已连接设备列表
      const refreshConnectedList = async () => {
        try {
          refData.loading.value = true;
          const rsp = await bluetoothAction("connected", "GET");
          if (rsp.code === 0) {
            refData.connectedDeviceList.value = rsp.data || [];
          } else {
            ElMessage.error(rsp.msg || "获取已连接设备失败");
          }
        } catch (error) {
          console.error("获取已连接设备失败:", error);
          ElMessage.error("获取已连接设备失败");
        } finally {
          refData.loading.value = false;
        }
      };
      // 连接设备
      const handleConnectDevice = async (device) => {
        try {
          device.connecting = true;
          const rsp = await bluetoothAction("connect", "POST", {
            address: device.address,
          });
          if (rsp.code === 0) {
            ElMessage.success(`成功连接到设备: ${device.name}`);
            // 刷新已连接设备列表
            await refreshConnectedList();
            // 从扫描列表中移除已连接的设备
            refData.deviceList.value = refData.deviceList.value.filter(
              (d) => d.address !== device.address
            );
          } else {
            ElMessage.error(rsp.msg || "连接失败");
          }
        } catch (error) {
          console.error("连接设备失败:", error);
          ElMessage.error("连接设备失败");
        } finally {
          device.connecting = false;
        }
      };

      // 断开设备
      const handleDisconnectDevice = async (device) => {
        try {
          device.disconnecting = true;
          const rsp = await bluetoothAction("disconnect", "POST", {
            address: device.address,
          });
          if (rsp.code === 0) {
            ElMessage.success(`已断开设备: ${device.name}`);
            // 刷新已连接设备列表
            await refreshConnectedList();
          } else {
            ElMessage.error(rsp.msg || "断开失败");
          }
        } catch (error) {
          console.error("断开设备失败:", error);
          ElMessage.error("断开设备失败");
        } finally {
          device.disconnecting = false;
        }
      };

      // 扫描设备
      const handleUpdateDeviceList = async () => {
        try {
          refData.loading.value = true;
          const rsp = await bluetoothAction("scan", "GET");
          if (rsp.code === 0) {
            refData.deviceList.value = (rsp.data || []).map(device => ({
              ...device,
              connecting: false,
            }));
            ElMessage.success(`扫描完成，找到 ${refData.deviceList.value.length} 个设备`);
          } else {
            ElMessage.error(rsp.msg || "扫描失败");
          }
        } catch (error) {
          console.error("扫描设备失败:", error);
          ElMessage.error("扫描设备失败");
        } finally {
          refData.loading.value = false;
        }
      };

      // 打开扫描弹窗
      const handleOpenScanDialog = () => {
        refData.scanDialogVisible.value = true;
        // 打开弹窗时自动扫描
        // handleUpdateDeviceList();
      };

      // 关闭扫描弹窗
      const handleCloseScanDialog = () => {
        refData.scanDialogVisible.value = false;
      };

      // 打开目录选择弹窗
      const handleOpenDirectoryDialog = () => {
        refData.directoryDialogVisible.value = true;
        // 如果没有已选择的路径，使用默认路径 /mnt
        refData.currentPath.value = refData.selectedPath.value || "/mnt";
        handleRefreshDirectory();
      };

      // 关闭目录选择弹窗
      const handleCloseDirectoryDialog = () => {
        refData.directoryDialogVisible.value = false;
      };

      // 刷新目录列表
      const handleRefreshDirectory = async () => {
        try {
          refData.directoryLoading.value = true;
          const path = refData.currentPath.value || "/mnt";
          const rsp = await bluetoothAction("listDirectory", "GET", {
            path: path,
          });
          if (rsp.code === 0) {
            refData.directoryList.value = rsp.data || [];
            // 更新当前路径（后端可能返回实际使用的路径）
            if (rsp.currentPath) {
              refData.currentPath.value = rsp.currentPath;
            }
            updateCanNavigateUp();
          } else {
            ElMessage.error(rsp.msg || "获取目录列表失败");
            // 如果失败，尝试重置到默认路径
            if (refData.currentPath.value && refData.currentPath.value !== "/mnt") {
              refData.currentPath.value = "/mnt";
              // 不自动重试，让用户手动刷新
            }
          }
        } catch (error) {
          console.error("获取目录列表失败:", error);
          ElMessage.error("获取目录列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.directoryLoading.value = false;
        }
      };

      // 导航到上一级
      const handleNavigateUp = () => {
        const path = refData.currentPath.value;
        if (path && path !== "/mnt" && path !== "/") {
          const parts = path.split("/").filter(p => p);
          parts.pop();
          refData.currentPath.value = parts.length > 0 ? "/" + parts.join("/") : "/mnt";
          updateCanNavigateUp();
          handleRefreshDirectory();
        }
      };

      // 导航到首页（默认目录）
      const handleGoToHome = () => {
        refData.currentPath.value = "/mnt";
        updateCanNavigateUp();
        handleRefreshDirectory();
      };

      // 点击目录行
      const handleDirectoryRowClick = (row) => {
        if (row.isDirectory) {
          const newPath = refData.currentPath.value === "/" 
            ? `/${row.name}` 
            : `${refData.currentPath.value}/${row.name}`;
          refData.currentPath.value = newPath;
          updateCanNavigateUp();
          handleRefreshDirectory();
        }
      };

      // 选择目录
      const handleSelectDirectory = (row) => {
        const selectedPath = refData.currentPath.value === "/" 
          ? `/${row.name}` 
          : `${refData.currentPath.value}/${row.name}`;
        refData.selectedPath.value = selectedPath;
        handleCloseDirectoryDialog();
        ElMessage.success(`已选择目录: ${selectedPath}`);
        // 选择目录后，加载文件列表
        loadFileList(selectedPath);
        // 自动保存配置
        saveBluetoothConfig();
      };

      // 打开 Cron 生成器
      const handleOpenCronBuilder = () => {
        refData.cronBuilderVisible.value = true;
        // 如果已有表达式，尝试解析
        if (refData.cronExpression.value) {
          parseCronExpression(refData.cronExpression.value);
        } else {
          // 重置为默认值
          resetCronBuilder();
        }
      };

      // 关闭 Cron 生成器
      const handleCloseCronBuilder = () => {
        refData.cronBuilderVisible.value = false;
      };

      // 重置 Cron 生成器
      const resetCronBuilder = () => {
        refData.cronBuilder.value = {
          second: "*",
          secondCustom: "",
          minute: "*",
          minuteCustom: "",
          hour: "*",
          hourCustom: "",
          day: "*",
          dayCustom: "",
          month: "*",
          monthCustom: "",
          weekday: "*",
          weekdayCustom: "",
          generated: "",
        };
        updateCronExpression();
      };

      // 解析 Cron 表达式到生成器
      const parseCronExpression = (cronExpr) => {
        try {
          console.log("开始解析 Cron 表达式:", cronExpr);
          const parts = cronExpr.trim().split(/\s+/);
          console.log("分割后的部分:", parts, "长度:", parts.length);
          
          let sec, min, hour, day, month, weekday;
          
          // 支持标准格式（5部分）和扩展格式（6部分）
          if (parts.length === 5) {
            // 标准格式：分 时 日 月 周
            // 对于 "0 */30 * * *" 这种，第一个 0 是分钟，*/30 也是分钟的一部分
            // 但更合理的理解是：0 是分钟，*/30 是小时（每30小时），这不对
            // 实际上用户想要的是"每30分钟"，所以应该理解为：
            // 第一个值如果是数字，可能是分钟；如果第二个值是 */30，更可能是分钟
            // 为了简化，我们假设 5 部分格式中，第一个是分钟，第二个是小时
            // 但用户示例 "0 */30 * * *" 想要的是每30分钟，所以需要特殊处理
            const [first, second, third, fourth, fifth] = parts;
            
            // 如果第二个值是 */30 或类似格式，且第一个值是 0，很可能是"每30分钟"
            // 这种情况下，应该理解为：秒=0, 分=*/30, 时=*, 日=*, 月=*, 周=*
            if (first === "0" && second && second.startsWith("*/")) {
              // 特殊处理：每X分钟的情况
              sec = "0";
              min = second;  // */30
              hour = third || "*";
              day = fourth || "*";
              month = fifth || "*";
              weekday = "*";
            } else {
              // 标准格式：分 时 日 月 周，秒默认为 "0"
              min = first;
              hour = second;
              day = third;
              month = fourth;
              weekday = fifth;
              sec = "0";
            }
          } else if (parts.length === 6) {
            // 扩展格式：秒 分 时 日 月 周
            [sec, min, hour, day, month, weekday] = parts;
          } else {
            console.warn("Cron 表达式格式错误，部分数量:", parts.length);
            resetCronBuilder();
            return;
          }
          
          if (parts.length === 5 || parts.length === 6) {
            
            console.log("解析 Cron 表达式:", cronExpr, "各部分:", { sec, min, hour, day, month, weekday });
            
            // 直接更新 ref 对象的每个属性，确保 Vue 响应式
            // 解析秒
            if (sec === "*") {
              refData.cronBuilder.value.second = "*";
              refData.cronBuilder.value.secondCustom = "";
            } else if (sec === "0") {
              refData.cronBuilder.value.second = "0";
              refData.cronBuilder.value.secondCustom = "";
            } else {
              refData.cronBuilder.value.second = "custom";
              refData.cronBuilder.value.secondCustom = sec;
            }
            
            // 解析分
            if (min === "*") {
              refData.cronBuilder.value.minute = "*";
              refData.cronBuilder.value.minuteCustom = "";
            } else if (min === "0") {
              refData.cronBuilder.value.minute = "0";
              refData.cronBuilder.value.minuteCustom = "";
            } else if (min.startsWith("*/")) {
              // 处理步长格式：*/30, */15 等
              refData.cronBuilder.value.minute = "custom";
              refData.cronBuilder.value.minuteCustom = min;
            } else {
              refData.cronBuilder.value.minute = "custom";
              refData.cronBuilder.value.minuteCustom = min;
            }
            
            // 解析时
            if (hour === "*") {
              refData.cronBuilder.value.hour = "*";
              refData.cronBuilder.value.hourCustom = "";
            } else if (hour === "0") {
              refData.cronBuilder.value.hour = "0";
              refData.cronBuilder.value.hourCustom = "";
            } else {
              refData.cronBuilder.value.hour = "custom";
              refData.cronBuilder.value.hourCustom = hour;
            }
            
            // 解析日
            if (day === "*") {
              refData.cronBuilder.value.day = "*";
              refData.cronBuilder.value.dayCustom = "";
            } else {
              refData.cronBuilder.value.day = "custom";
              refData.cronBuilder.value.dayCustom = day;
            }
            
            // 解析月
            if (month === "*") {
              refData.cronBuilder.value.month = "*";
              refData.cronBuilder.value.monthCustom = "";
            } else {
              refData.cronBuilder.value.month = "custom";
              refData.cronBuilder.value.monthCustom = month;
            }
            
            // 解析周
            if (weekday === "*") {
              refData.cronBuilder.value.weekday = "*";
              refData.cronBuilder.value.weekdayCustom = "";
            } else if (weekday === "1-5") {
              refData.cronBuilder.value.weekday = "1-5";
              refData.cronBuilder.value.weekdayCustom = "";
            } else if (weekday === "0,6" || weekday === "6,0") {
              refData.cronBuilder.value.weekday = "0,6";
              refData.cronBuilder.value.weekdayCustom = "";
            } else {
              refData.cronBuilder.value.weekday = "custom";
              refData.cronBuilder.value.weekdayCustom = weekday;
            }
            
            console.log("解析完成，当前状态:", JSON.parse(JSON.stringify(refData.cronBuilder.value)));
            
            // 立即更新生成的表达式
            updateCronExpression();
            
            console.log("解析后的最终状态:", JSON.parse(JSON.stringify(refData.cronBuilder.value)));
          } else {
            console.warn("Cron 表达式格式错误，部分数量:", parts.length);
            resetCronBuilder();
          }
        } catch (error) {
          console.error("解析 Cron 表达式失败:", error);
          resetCronBuilder();
        }
      };

      // 更新生成的 Cron 表达式
      const updateCronExpression = () => {
        const builder = refData.cronBuilder.value;
        
        const second = builder.second === "custom" 
          ? (builder.secondCustom || "*") 
          : (builder.second || "*");
        const minute = builder.minute === "custom" 
          ? (builder.minuteCustom || "*") 
          : (builder.minute || "*");
        const hour = builder.hour === "custom" 
          ? (builder.hourCustom || "*") 
          : (builder.hour || "*");
        const day = builder.day === "custom" 
          ? (builder.dayCustom || "*") 
          : (builder.day || "*");
        const month = builder.month === "custom" 
          ? (builder.monthCustom || "*") 
          : (builder.month || "*");
        const weekday = builder.weekday === "custom" 
          ? (builder.weekdayCustom || "*") 
          : (builder.weekday || "*");
        
        const generated = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
        refData.cronBuilder.value.generated = generated;
        
        console.log("更新生成的表达式:", generated, "当前状态:", {
          second: builder.second,
          secondCustom: builder.secondCustom,
          minute: builder.minute,
          minuteCustom: builder.minuteCustom,
          hour: builder.hour,
          hourCustom: builder.hourCustom,
          day: builder.day,
          dayCustom: builder.dayCustom,
          month: builder.month,
          monthCustom: builder.monthCustom,
          weekday: builder.weekday,
          weekdayCustom: builder.weekdayCustom,
        });
      };

      // 保存配置
      const saveBluetoothConfig = async () => {
        try {
          const configData = {
            cron_expression: refData.cronExpression.value,
            selected_path: refData.selectedPath.value,
            // file_list 不保存，需要时重新获取
            // connected_devices 不保存，由 refreshConnectedList 获取实时数据
          };
          await setRdsData("SCHELUE_PLAY", "bluetooth", JSON.stringify(configData));
        } catch (error) {
          console.error("保存配置失败:", error);
        }
      };

      // 加载配置
      const loadBluetoothConfig = async () => {
        try {
          const dataStr = await getRdsData("SCHELUE_PLAY", "bluetooth");
          if (dataStr) {
            const data = JSON.parse(dataStr);
            if (data.cron_expression) {
              refData.cronExpression.value = data.cron_expression;
            }
            if (data.selected_path) {
              refData.selectedPath.value = data.selected_path;
              // 重新获取文件列表（不保存，需要时重新获取）
              await loadFileList(data.selected_path);
            }
            // 注意：file_list 不加载，由 loadFileList 重新获取
            // 注意：connected_devices 由 refreshConnectedList 获取实时数据
          }
        } catch (error) {
          console.error("加载配置失败:", error);
        }
      };

      // 更新下次运行时间
      const updateNextRunTime = () => {
        if (!refData.cronExpression.value) {
          refData.nextRunTime.value = "";
          return;
        }
        try {
          const times = calculateNextCronTimes(refData.cronExpression.value, 1);
          if (times && times.length > 0) {
            refData.nextRunTime.value = times[0];
          } else {
            refData.nextRunTime.value = "";
          }
        } catch (error) {
          refData.nextRunTime.value = "";
        }
      };

      // 应用生成的 Cron 表达式
      const handleApplyCronExpression = () => {
        if (refData.cronBuilder.value.generated) {
          refData.cronExpression.value = refData.cronBuilder.value.generated;
          handleCloseCronBuilder();
          ElMessage.success("Cron 表达式已应用");
          // 更新下次运行时间
          updateNextRunTime();
          // 自动保存配置
          saveBluetoothConfig();
        }
      };

      // 应用示例
      const applyExample = (example) => {
        try {
          console.log("应用示例:", example);
          // 解析并更新生成器
          parseCronExpression(example);
          // 使用 nextTick 确保 Vue 响应式更新完成后再验证
          nextTick(() => {
            const currentGenerated = refData.cronBuilder.value.generated;
            console.log("更新后的生成器状态:", JSON.parse(JSON.stringify(refData.cronBuilder.value)));
            console.log("生成的表达式:", currentGenerated);
            
            // 判断示例是5部分还是6部分格式
            const exampleParts = example.trim().split(/\s+/);
            const isExample5Parts = exampleParts.length === 5;
            
            // 验证生成的表达式是否正确
            let shouldMatch = false;
            if (isExample5Parts) {
              // 如果示例是5部分格式，将生成的6部分格式转换为5部分格式（去掉秒部分）进行比较
              const generatedParts = currentGenerated.trim().split(/\s+/);
              if (generatedParts.length === 6) {
                // 检查是否是特殊格式：示例 "0 */30 * * *" 被解析为秒=0, 分=*/30
                if (exampleParts[0] === "0" && exampleParts[1] && exampleParts[1].startsWith("*/")) {
                  // 特殊格式：第一个是 "0"，第二个是 "*/X"，这被解析为秒=0, 分=*/X
                  // 生成的应该是 "0 */30 * * * *"，转换为5部分后应该是 "*/30 * * * *"
                  // 但示例是 "0 */30 * * *"，所以需要特殊处理
                  // 实际上，我们的解析逻辑将 "0 */30 * * *" 解析为秒=0, 分=*/30, 时=*, 日=*, 月=*, 周=*
                  // 所以生成的 "0 */30 * * * *" 是正确的
                  // 验证时，我们检查生成的表达式是否符合解析逻辑
                  // 对于特殊格式 "0 */30 * * *" (5部分)，解析为：秒=0, 分=*/30, 时=*, 日=*, 月=*, 周=*
                  // 生成的表达式应该是 "0 */30 * * * *" (6部分)
                  shouldMatch = generatedParts[0] === "0" && 
                                generatedParts[1] === exampleParts[1] && // 分 = */30
                                generatedParts[2] === exampleParts[2] && // 时 = *
                                generatedParts[3] === exampleParts[3] && // 日 = *
                                generatedParts[4] === exampleParts[4] && // 月 = *
                                generatedParts[5] === "*"; // 周 = * (示例没有周部分，默认为 "*")
                  console.log("特殊格式验证:", {
                    generated: currentGenerated,
                    example: example,
                    generatedParts: generatedParts,
                    exampleParts: exampleParts,
                    shouldMatch: shouldMatch,
                    details: {
                      secMatch: generatedParts[0] === "0",
                      minMatch: generatedParts[1] === exampleParts[1],
                      hourMatch: generatedParts[2] === exampleParts[2],
                      dayMatch: generatedParts[3] === exampleParts[3],
                      monthMatch: generatedParts[4] === exampleParts[4],
                      weekdayMatch: generatedParts[5] === "*"
                    }
                  });
                } else {
                  // 标准格式：分 时 日 月 周，秒默认为 "0"
                  // 将生成的6部分格式转换为5部分格式（去掉秒部分）进行比较
                  const generated5Parts = generatedParts.slice(1).join(' '); // 去掉秒部分
                  shouldMatch = generated5Parts === example;
                  console.log("标准格式验证:", {
                    generated: currentGenerated,
                    generated5Parts: generated5Parts,
                    example: example,
                    shouldMatch: shouldMatch
                  });
                }
              }
            } else {
              // 如果示例是6部分格式，直接比较
              shouldMatch = currentGenerated === example;
            }
            
            if (!shouldMatch) {
              console.warn("生成的表达式与示例不匹配，当前:", currentGenerated, "期望:", example);
              // 不再重复解析，因为解析逻辑是正确的，只是格式不同
              // 5部分格式的示例会被正确解析为6部分格式的内部表示
            } else {
              console.log("验证通过：生成的表达式与示例匹配");
            }
          });
        } catch (error) {
          console.error("应用示例失败:", error);
          ElMessage.error("应用示例失败: " + error.message);
        }
      };

      // 解析 Cron 字段
      const parseCronField = (expr, min, max) => {
        if (expr === "*") {
          return null; // null 表示匹配所有值
        }
        
        const values = new Set();
        const parts = expr.split(",");
        
        for (const part of parts) {
          const trimmed = part.trim();
          if (trimmed.includes("/")) {
            // 步长：*/30 或 0-59/10
            const [range, step] = trimmed.split("/");
            const stepNum = parseInt(step, 10);
            if (range === "*") {
              for (let i = min; i <= max; i += stepNum) {
                values.add(i);
              }
            } else if (range.includes("-")) {
              const [start, end] = range.split("-").map(x => parseInt(x, 10));
              for (let i = start; i <= end; i += stepNum) {
                values.add(i);
              }
            }
          } else if (trimmed.includes("-")) {
            // 范围：1-5
            const [start, end] = trimmed.split("-").map(x => parseInt(x, 10));
            for (let i = start; i <= end; i++) {
              values.add(i);
            }
          } else {
            // 单个值
            const val = parseInt(trimmed, 10);
            if (!isNaN(val) && val >= min && val <= max) {
              values.add(val);
            }
          }
        }
        
        return values.size > 0 ? Array.from(values).sort((a, b) => a - b) : null;
      };

      // 计算 Cron 表达式的下 N 次执行时间
      const calculateNextCronTimes = (cronExpr, count = 3) => {
        try {
          const parts = cronExpr.trim().split(/\s+/);
          if (parts.length !== 6) {
            throw new Error("Cron 表达式必须包含6个字段：秒 分 时 日 月 周");
          }

          const [secExpr, minExpr, hourExpr, dayExpr, monthExpr, weekdayExpr] = parts;
          
          // 解析各个字段
          const seconds = parseCronField(secExpr, 0, 59);
          const minutes = parseCronField(minExpr, 0, 59);
          const hours = parseCronField(hourExpr, 0, 23);
          const days = parseCronField(dayExpr, 1, 31);
          const months = parseCronField(monthExpr, 1, 12);
          let weekdays = parseCronField(weekdayExpr, 0, 7);
          
          // 处理周字段：7 和 0 都表示周日
          if (weekdays && weekdays.includes(7)) {
            weekdays = weekdays.filter(d => d !== 7);
            if (!weekdays.includes(0)) {
              weekdays.push(0);
            }
            weekdays.sort((a, b) => a - b);
          }

          const times = [];
          const current = new Date();
          current.setMilliseconds(0);
          
          // 如果当前秒不在范围内，跳到下一分钟
          if (seconds && !seconds.includes(current.getSeconds())) {
            current.setSeconds(0);
            current.setMinutes(current.getMinutes() + 1);
          }

          let iterations = 0;
          const maxIterations = 10000;

          while (times.length < count && iterations < maxIterations) {
            iterations++;

            // 检查月份
            const currentMonth = current.getMonth() + 1; // getMonth() 返回 0-11
            if (months && !months.includes(currentMonth)) {
              // 跳到下一个有效月份的第一天
              let nextMonth = null;
              for (const m of months) {
                if (m > currentMonth) {
                  nextMonth = m;
                  break;
                }
              }
              if (nextMonth === null) {
                // 跳到下一年的第一个有效月份
                nextMonth = months[0];
                current.setFullYear(current.getFullYear() + 1, nextMonth - 1, 1);
                current.setHours(0, 0, seconds ? seconds[0] : 0);
              } else {
                current.setMonth(nextMonth - 1, 1);
                current.setHours(0, 0, seconds ? seconds[0] : 0);
              }
              continue;
            }

            // 检查日期和星期
            const currentDay = current.getDate();
            const currentWeekday = current.getDay(); // 0=周日, 1=周一, ..., 6=周六
            
            let validDay = true;
            if (dayExpr !== "*" && weekdayExpr !== "*") {
              // 两个都指定，满足任意一个即可（OR逻辑）
              validDay = (days && days.includes(currentDay)) || 
                        (weekdays && weekdays.includes(currentWeekday));
            } else if (dayExpr !== "*") {
              // 只检查日期
              validDay = days && days.includes(currentDay);
            } else if (weekdayExpr !== "*") {
              // 只检查星期
              validDay = weekdays && weekdays.includes(currentWeekday);
            }

            if (!validDay) {
              current.setDate(current.getDate() + 1);
              current.setHours(0, 0, seconds ? seconds[0] : 0);
              continue;
            }

            // 检查小时
            const currentHour = current.getHours();
            if (hours && !hours.includes(currentHour)) {
              // 跳到下一个有效小时
              let nextHour = null;
              for (const h of hours) {
                if (h > currentHour) {
                  nextHour = h;
                  break;
                }
              }
              if (nextHour === null) {
                // 跳到下一天的第一个有效小时
                current.setDate(current.getDate() + 1);
                current.setHours(hours[0], 0, seconds ? seconds[0] : 0);
              } else {
                current.setHours(nextHour, 0, seconds ? seconds[0] : 0);
              }
              continue;
            }

            // 检查分钟
            const currentMinute = current.getMinutes();
            if (minutes && !minutes.includes(currentMinute)) {
              // 跳到下一个有效分钟
              let nextMinute = null;
              for (const m of minutes) {
                if (m > currentMinute) {
                  nextMinute = m;
                  break;
                }
              }
              if (nextMinute === null) {
                // 跳到下一个有效小时的第一分钟
                let nextHour = null;
                for (const h of hours || [currentHour]) {
                  if (h > currentHour) {
                    nextHour = h;
                    break;
                  }
                }
                if (nextHour === null) {
                  current.setDate(current.getDate() + 1);
                  current.setHours(hours ? hours[0] : 0, minutes[0], seconds ? seconds[0] : 0);
                } else {
                  current.setHours(nextHour, minutes[0], seconds ? seconds[0] : 0);
                }
              } else {
                current.setMinutes(nextMinute, seconds ? seconds[0] : 0);
              }
              continue;
            }

            // 检查秒
            const currentSecond = current.getSeconds();
            if (seconds && !seconds.includes(currentSecond)) {
              // 跳到下一个有效秒
              let nextSecond = null;
              for (const s of seconds) {
                if (s > currentSecond) {
                  nextSecond = s;
                  break;
                }
              }
              if (nextSecond === null) {
                // 跳到下一分钟的第一个有效秒
                current.setMinutes(current.getMinutes() + 1);
                current.setSeconds(seconds[0]);
              } else {
                current.setSeconds(nextSecond);
              }
              continue;
            }

            // 检查是否在未来
            if (current > new Date()) {
              const timeStr = current.getFullYear() + "-" +
                String(current.getMonth() + 1).padStart(2, "0") + "-" +
                String(current.getDate()).padStart(2, "0") + " " +
                String(current.getHours()).padStart(2, "0") + ":" +
                String(current.getMinutes()).padStart(2, "0") + ":" +
                String(current.getSeconds()).padStart(2, "0");
              times.push(timeStr);
            }

            // 移动到下一个可能的执行时间
            if (seconds && seconds.length > 0) {
              current.setSeconds(seconds[0]);
            }
            current.setMinutes(current.getMinutes() + 1);
          }

          return times.slice(0, count);
        } catch (error) {
          console.error("计算 Cron 执行时间失败:", error);
          throw error;
        }
      };

      // 预览生成的 Cron 表达式
      const handlePreviewGeneratedCron = () => {
        const cronExpr = refData.cronBuilder.value.generated;
        if (!cronExpr) {
          ElMessage.warning("请先生成 Cron 表达式");
          return;
        }
        try {
          const times = calculateNextCronTimes(cronExpr, 3);
          refData.cronPreviewTimes.value = times;
          refData.cronPreviewVisible.value = true;
        } catch (error) {
          ElMessage.error("预览失败: " + (error.message || "无效的 Cron 表达式"));
          refData.cronPreviewTimes.value = [];
        }
      };

      // 预览 Cron 表达式
      const handlePreviewCron = () => {
        if (!refData.cronExpression.value) {
          ElMessage.warning("请输入 Cron 表达式");
          return;
        }
        try {
          const times = calculateNextCronTimes(refData.cronExpression.value, 3);
          refData.cronPreviewTimes.value = times;
          refData.cronPreviewVisible.value = true;
        } catch (error) {
          ElMessage.error("预览失败: " + (error.message || "无效的 Cron 表达式"));
          refData.cronPreviewTimes.value = [];
        }
      };

      // 加载文件列表
      const loadFileList = async (path) => {
        if (!path) {
          refData.fileList.value = [];
          return;
        }
        try {
          refData.fileListLoading.value = true;
          const rsp = await bluetoothAction("listDirectory", "GET", {
            path: path,
          });
          if (rsp.code === 0) {
            // 只显示文件，不显示目录
            refData.fileList.value = (rsp.data || [])
              .filter(item => !item.isDirectory && item.accessible !== false)
              .map(item => item.name)
              .sort();
          } else {
            refData.fileList.value = [];
            ElMessage.warning(rsp.msg || "获取文件列表失败");
          }
        } catch (error) {
          console.error("获取文件列表失败:", error);
          refData.fileList.value = [];
        } finally {
          refData.fileListLoading.value = false;
        }
      };

      // 格式化文件大小
      const formatSize = (bytes) => {
        if (!bytes) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
      };

      // 计算是否可以导航到上一级（使用 computed）
      const canNavigateUp = ref(false);
      const updateCanNavigateUp = () => {
        const path = refData.currentPath.value;
        canNavigateUp.value = path && path !== "/mnt" && path !== "/";
      };

      const refMethods = {
        handleUpdateDeviceList,
        handleOpenScanDialog,
        handleCloseScanDialog,
        handleOpenDirectoryDialog,
        handleCloseDirectoryDialog,
        handleRefreshDirectory,
        handleNavigateUp,
        handleGoToHome,
        handleDirectoryRowClick,
        handleSelectDirectory,
        handleOpenCronBuilder,
        handleCloseCronBuilder,
        updateCronExpression,
        handleApplyCronExpression,
        applyExample,
        handlePreviewGeneratedCron,
        handlePreviewCron,
        updateNextRunTime,
        loadFileList,
        formatSize,
        handleConnectDevice,
        handleDisconnectDevice,
        refreshConnectedList,
        handleDialogClose: () => {
          refData.dialogForm.value.visible = false;
          refData.dialogForm.value.value = 0;
        },
      };
      
      // 初始化 canNavigateUp
      updateCanNavigateUp();
      
      onMounted(async () => {
        await refreshConnectedList();
        // 延迟加载配置，确保所有函数都已定义
        setTimeout(async () => {
          await loadBluetoothConfig();
          // 加载配置后更新下次运行时间
          updateNextRunTime();
        }, 100);
      });
      
      // 监听 Cron 表达式变化，自动更新下次运行时间（在 onMounted 之后设置）
      watch(() => refData.cronExpression.value, () => {
        updateNextRunTime();
      });
      return {
        ...refData,
        canNavigateUp,
        ...refMethods,
      };
    },
    template,
  };
  return component;
}
export default createComponent();
