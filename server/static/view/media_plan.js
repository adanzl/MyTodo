import { bluetoothAction, getApiUrl } from "../js/net_util.js";
import { createPlaylistId, formatDuration, calculateNextCronTimes, generateCronExpression } from "../js/utils.js";
import { createFileDialog } from "./common/file_dialog.js";
const axios = window.axios;

const { ref, watch, onMounted, nextTick } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;
let component = null;

async function loadTemplate() {
  const response = await fetch(`./view/media_plan-template.html?t=${Date.now()}`);
  return await response.text();
}

async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  
  // 加载文件对话框组件
  const FileDialog = await createFileDialog();
  
  component = {
    components: {
      FileDialog,
    },
    setup() {
      const refData = {
        scanDialogVisible: ref(false),
        fileBrowserDialogVisible: ref(false),
        fileBrowserTarget: ref(null), // "main_list" 或 "pre_list_{index}"
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
        cronBuilderVisible: ref(false),
        cronPreviewVisible: ref(false),
        cronPreviewTimes: ref([]),
        editingPlanId: ref(null),
        editingPlanName: ref(""),
        loading: ref(false),
        deviceList: ref([]),
        connectedDeviceList: ref([]),
        playing: ref(false),
        stopping: ref(false),
        planCollection: ref([]),
        activePlanId: ref(""),
        planStatus: ref(null),
        planLoading: ref(false),
        planRefreshing: ref(false),
      };
      const pendingDeviceType = ref(null);

      // 规范化文件列表格式
      const normalizeFiles = (files) => {
        if (!Array.isArray(files)) return [];
        return files.map((fileItem) => {
          if (!fileItem || typeof fileItem !== "object") return null;
          return {
            uri: fileItem.uri || fileItem.path || fileItem.file || "",
            duration: fileItem.duration || null,
          };
        }).filter((item) => item !== null);
      };

      // 创建默认计划
      const createDefaultPlan = (overrides = {}) => ({
        id: overrides.id || createPlaylistId(),
        name: overrides.name || "默认计划",
        enabled: overrides.enabled || 0,
        pre_lists: overrides.pre_lists || [],
        main_list: overrides.main_list || { files: [] },
        device_address: overrides.device_address || null,
        device_type: overrides.device_type || "dlna",
        device: overrides.device || { type: "dlna", address: null, name: null },
        schedule: overrides.schedule || { enabled: 0, cron: "", duration: 0 },
      });

      // 规范化计划项
      const normalizePlanItem = (item, fallbackName = "计划") => {
        const name = (item?.name && String(item.name).trim()) || fallbackName;
        const deviceType = item?.device?.type || item?.device_type || "dlna";
        const validDeviceType = ["agent", "dlna", "bluetooth", "mi"].includes(deviceType)
          ? deviceType
          : "dlna";
        const schedule = item?.schedule || { enabled: 0, cron: "", duration: 0 };
        const normalizedSchedule = {
          enabled: schedule.enabled || 0,
          cron: (schedule.cron !== undefined && schedule.cron !== null) ? String(schedule.cron) : "",
          duration: schedule.duration || 0,
        };

        return {
          id: item?.id || createPlaylistId(),
          name,
          enabled: item?.enabled || 0,
          pre_lists: (item?.pre_lists || []).map(preList => ({
            weekdays: preList.weekdays || [],
            files: normalizeFiles(preList.files || []),
          })),
          main_list: {
            files: normalizeFiles(item?.main_list?.files || []),
          },
          device_address: item?.device_address || item?.device?.address || null,
          device_type: validDeviceType,
          device: item?.device || { type: validDeviceType, address: item?.device_address || null, name: item?.device?.name || null },
          schedule: normalizedSchedule,
        };
      };

      // 规范化计划集合
      const normalizePlanCollection = (raw) => {
        if (!raw || typeof raw !== 'object') {
          const defaultPlan = normalizePlanItem(createDefaultPlan());
          return { plans: [defaultPlan], activePlanId: defaultPlan.id };
        }

        // 如果是字典格式 {plan_id: plan_data}
        const planEntries = Object.entries(raw);
        if (planEntries.length === 0) {
          const defaultPlan = normalizePlanItem(createDefaultPlan());
          return { plans: [defaultPlan], activePlanId: defaultPlan.id };
        }

        const plans = planEntries.map(([id, data]) => {
          const planData = typeof data === 'object' ? data : {};
          return normalizePlanItem({ ...planData, id }, planData?.name || `计划${id}`);
        });

        const activeId = plans[0]?.id || "";
        return { plans, activePlanId: activeId };
      };

      // 保存/恢复选中的计划ID
      const saveActivePlanId = (planId) => {
        try {
          if (planId) {
            localStorage.setItem('active_plan_id', planId);
          }
        } catch (error) {
          console.warn("保存选中计划ID失败:", error);
        }
      };

      const restoreActivePlanId = () => {
        try {
          return localStorage.getItem('active_plan_id');
        } catch (error) {
          console.warn("恢复选中计划ID失败:", error);
        }
        return null;
      };

      // 更新活动计划数据（单个计划更新）
      const updateActivePlanData = async (updater) => {
        if (!refData.planStatus.value) return;
        const updated = updater({ ...refData.planStatus.value });
        refData.planStatus.value = updated;
        
        // 同步到集合中
        const index = refData.planCollection.value.findIndex(p => p.id === updated.id);
        if (index >= 0) {
          refData.planCollection.value[index] = { ...updated };
        }
        
        // 调用单个计划更新接口
        await updateSinglePlan(updated);
      };

      // 更新单个计划
      const updateSinglePlan = async (plan) => {
        try {
          const response = await axios.post(`${getApiUrl()}/plan/update`, plan);
          if (response.data && response.data.code === 0) {
            return true;
          } else {
            ElMessage.error(response.data?.msg || "更新计划失败");
            return false;
          }
        } catch (error) {
          console.error("更新计划失败:", error);
          ElMessage.error("更新计划失败: " + (error.message || "未知错误"));
          return false;
        }
      };

      // 保存整个计划集合（覆盖更新）
      const savePlan = async (plans) => {
        try {
          const planDict = {};
          plans.forEach(plan => {
            planDict[plan.id] = plan;
          });
          const response = await axios.post(`${getApiUrl()}/plan/updateAll`, planDict);
          if (response.data && response.data.code === 0) {
            return true;
          } else {
            ElMessage.error(response.data?.msg || "保存计划集合失败");
            return false;
          }
        } catch (error) {
          console.error("保存计划集合失败:", error);
          ElMessage.error("保存计划集合失败: " + (error.message || "未知错误"));
          return false;
        }
      };

      // 加载计划
      const loadPlan = async () => {
        try {
          refData.planLoading.value = true;
          const response = await axios.get(`${getApiUrl()}/plan/get`);
          if (response.data && response.data.code === 0) {
            const normalized = normalizePlanCollection(response.data.data);
            refData.planCollection.value = normalized.plans;
            
            // 恢复或设置活动计划ID
            const savedId = restoreActivePlanId();
            if (savedId && normalized.plans.some(p => p.id === savedId)) {
              refData.activePlanId.value = savedId;
            } else if (normalized.plans.length > 0) {
              refData.activePlanId.value = normalized.plans[0].id;
              saveActivePlanId(normalized.plans[0].id);
            }
            
            // 同步活动计划状态
            syncActivePlan(refData.planCollection.value);
          } else {
            ElMessage.error(response.data?.msg || "加载计划失败");
          }
        } catch (error) {
          console.error("加载计划失败:", error);
          ElMessage.error("加载计划失败: " + (error.message || "未知错误"));
        } finally {
          refData.planLoading.value = false;
        }
      };

      // 同步活动计划状态
      const syncActivePlan = (plans) => {
        if (!refData.activePlanId.value) return;
        const activePlan = plans.find(p => p.id === refData.activePlanId.value);
        if (activePlan) {
          refData.planStatus.value = { ...activePlan };
        } else {
          refData.planStatus.value = null;
        }
      };

      // 刷新计划状态
      const refreshPlanStatus = async () => {
        refData.planRefreshing.value = true;
        try {
          await loadPlan();
          ElMessage.success("刷新成功");
        } catch (error) {
          console.error("刷新失败:", error);
        } finally {
          refData.planRefreshing.value = false;
        }
      };

      // 选择计划
      const handleSelectPlan = (planId) => {
        refData.activePlanId.value = planId;
        saveActivePlanId(planId);
        syncActivePlan(refData.planCollection.value);
      };

      // 创建计划
      const handleCreatePlan = async () => {
        try {
          const defaultName = `计划${refData.planCollection.value.length + 1}`;
          const { value } = await ElMessageBox.prompt("请输入计划名称", "新建计划", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            inputValue: defaultName,
            inputPlaceholder: defaultName,
            inputValidator: (val) => (!!val && val.trim().length > 0) || "名称不能为空",
          });
          const planName = (value || defaultName).trim();
          const newPlan = normalizePlanItem(createDefaultPlan({ name: planName }));
          const updated = [...refData.planCollection.value, newPlan];
          refData.planCollection.value = updated;
          refData.activePlanId.value = newPlan.id;
          saveActivePlanId(newPlan.id);
          syncActivePlan(updated);
          await savePlan(updated);
          ElMessage.success("计划已创建");
        } catch (error) {
          if (error === "cancel") return;
          console.error("创建计划失败:", error);
          ElMessage.error("创建计划失败: " + (error.message || "未知错误"));
        }
      };

      // 计划菜单命令
      const handlePlanMenuCommand = async (command, planId) => {
        if (command === "delete") {
          await handleDeletePlan(planId);
        } else if (command === "copy") {
          await handleCopyPlan(planId);
        }
      };

      // 删除计划
      const handleDeletePlan = async (planId) => {
        if (!planId) return;
        if (refData.planCollection.value.length <= 1) {
          ElMessage.warning("至少保留一个计划");
          return;
        }
        const target = refData.planCollection.value.find((item) => item.id === planId);
        if (!target) return;
        try {
          await ElMessageBox.confirm(`确认删除计划"${target.name}"吗？`, "删除计划", {
            confirmButtonText: "删除",
            cancelButtonText: "取消",
            type: "warning",
          });
          const updated = refData.planCollection.value.filter((item) => item.id !== planId);
          refData.planCollection.value = updated;
          
          if (planId === refData.activePlanId.value && updated.length > 0) {
            refData.activePlanId.value = updated[0].id;
            saveActivePlanId(updated[0].id);
          }
          
          syncActivePlan(updated);
          await savePlan(updated);
          ElMessage.success("计划已删除");
        } catch (error) {
          if (error === "cancel") return;
          console.error("删除计划失败:", error);
          ElMessage.error("删除计划失败: " + (error.message || "未知错误"));
        }
      };

      // 复制计划
      const handleCopyPlan = async (planId) => {
        if (!planId) return;
        const sourcePlan = refData.planCollection.value.find((item) => item.id === planId);
        if (!sourcePlan) return;
        
        try {
          const defaultName = `${sourcePlan.name}_副本`;
          const { value } = await ElMessageBox.prompt("请输入计划名称", "复制计划", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            inputValue: defaultName,
            inputPlaceholder: defaultName,
            inputValidator: (val) => (!!val && val.trim().length > 0) || "名称不能为空",
          });
          const planName = (value || defaultName).trim();
          
          const copiedPlan = normalizePlanItem({
            ...sourcePlan,
            id: createPlaylistId(),
            name: planName,
          });
          
          const updated = [...refData.planCollection.value, copiedPlan];
          refData.planCollection.value = updated;
          refData.activePlanId.value = copiedPlan.id;
          saveActivePlanId(copiedPlan.id);
          syncActivePlan(updated);
          await savePlan(updated);
          ElMessage.success("计划已复制");
        } catch (error) {
          if (error === "cancel") return;
          console.error("复制计划失败:", error);
          ElMessage.error("复制计划失败: " + (error.message || "未知错误"));
        }
      };

      // 切换计划启用状态
      const handleTogglePlanEnabled = async (planId, enabled) => {
        const plan = refData.planCollection.value.find(p => p.id === planId);
        if (!plan) return;
        plan.enabled = enabled ? 1 : 0;
        await savePlan(refData.planCollection.value);
        syncActivePlan(refData.planCollection.value);
      };

      // 编辑计划名称
      const handleStartEditPlanName = (planId) => {
        const plan = refData.planCollection.value.find(p => p.id === planId);
        if (plan) {
          refData.editingPlanId.value = planId;
          refData.editingPlanName.value = plan.name;
          nextTick(() => {
            const input = refData.editPlanNameInput;
            if (input && input.$el) {
              input.$el.querySelector('input')?.focus();
            }
          });
        }
      };

      const handleSavePlanName = async (planId) => {
        if (refData.editingPlanId.value !== planId) return;
        const newName = (refData.editingPlanName.value || "").trim();
        if (!newName) {
          ElMessage.warning("名称不能为空");
          return;
        }
        await updateActivePlanData((planInfo) => {
          planInfo.name = newName;
          return planInfo;
        });
        refData.editingPlanId.value = null;
        refData.editingPlanName.value = "";
      };

      const handleCancelEditPlanName = () => {
        refData.editingPlanId.value = null;
        refData.editingPlanName.value = "";
      };

      // 添加前置列表
      const handleAddPreList = async () => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (!planInfo.pre_lists) {
            planInfo.pre_lists = [];
          }
          planInfo.pre_lists.push({
            weekdays: [],
            files: [],
          });
          return planInfo;
        });
      };

      // 删除前置列表
      const handleDeletePreList = async (preListIndex) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (planInfo.pre_lists && planInfo.pre_lists[preListIndex]) {
            planInfo.pre_lists.splice(preListIndex, 1);
          }
          return planInfo;
        });
      };

      // 切换前置列表星期
      const handleTogglePreListWeekday = async (preListIndex, weekday, checked) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (!planInfo.pre_lists || !planInfo.pre_lists[preListIndex]) return planInfo;
          const preList = planInfo.pre_lists[preListIndex];
          if (!preList.weekdays) {
            preList.weekdays = [];
          }
          if (checked) {
            if (!preList.weekdays.includes(weekday)) {
              preList.weekdays.push(weekday);
              preList.weekdays.sort();
            }
          } else {
            preList.weekdays = preList.weekdays.filter(w => w !== weekday);
          }
          return planInfo;
        });
      };

      // 打开文件浏览器（前置列表）
      const handleOpenFileBrowserForPreList = (preListIndex) => {
        if (!refData.planStatus.value) return;
        refData.fileBrowserTarget.value = `pre_list_${preListIndex}`;
        refData.fileBrowserDialogVisible.value = true;
      };

      // 打开文件浏览器（正式列表）
      const handleOpenFileBrowserForMainList = () => {
        if (!refData.planStatus.value) return;
        refData.fileBrowserTarget.value = "main_list";
        refData.fileBrowserDialogVisible.value = true;
      };

      // 关闭文件浏览器
      const handleCloseFileBrowser = () => {
        refData.fileBrowserDialogVisible.value = false;
        refData.fileBrowserTarget.value = null;
      };

      // 处理文件选择
      const handleFileSelected = async (filePaths) => {
        if (filePaths.length === 0) {
          handleCloseFileBrowser();
          return;
        }
        if (!refData.planStatus.value) {
          ElMessage.warning("请先选择一个计划");
          handleCloseFileBrowser();
          return;
        }

        try {
          refData.planLoading.value = true;
          const target = refData.fileBrowserTarget.value;
          
          await updateActivePlanData((planInfo) => {
            if (target === "main_list") {
              // 添加到正式列表
              if (!planInfo.main_list) {
                planInfo.main_list = { files: [] };
              }
              if (!planInfo.main_list.files) {
                planInfo.main_list.files = [];
              }
              const existingUris = new Set(planInfo.main_list.files.map(f => f.uri));
              filePaths.forEach(filePath => {
                if (!existingUris.has(filePath)) {
                  planInfo.main_list.files.push({ uri: filePath, duration: null });
                }
              });
            } else if (target && target.startsWith("pre_list_")) {
              // 添加到前置列表
              const preListIndex = parseInt(target.replace("pre_list_", ""));
              if (planInfo.pre_lists && planInfo.pre_lists[preListIndex]) {
                const preList = planInfo.pre_lists[preListIndex];
                if (!preList.files) {
                  preList.files = [];
                }
                const existingUris = new Set(preList.files.map(f => f.uri));
                filePaths.forEach(filePath => {
                  if (!existingUris.has(filePath)) {
                    preList.files.push({ uri: filePath, duration: null });
                  }
                });
              }
            }
            return planInfo;
          });
          
          handleCloseFileBrowser();
          ElMessage.success(`已添加 ${filePaths.length} 个文件`);
        } catch (error) {
          console.error("添加文件失败:", error);
          ElMessage.error("添加文件失败: " + (error.message || "未知错误"));
        } finally {
          refData.planLoading.value = false;
        }
      };

      // 删除前置列表文件
      const handleDeletePreListFile = async (preListIndex, fileIndex) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (planInfo.pre_lists && planInfo.pre_lists[preListIndex] && planInfo.pre_lists[preListIndex].files) {
            planInfo.pre_lists[preListIndex].files.splice(fileIndex, 1);
          }
          return planInfo;
        });
      };

      // 删除正式列表文件
      const handleDeleteMainListFile = async (fileIndex) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (planInfo.main_list && planInfo.main_list.files) {
            planInfo.main_list.files.splice(fileIndex, 1);
          }
          return planInfo;
        });
      };

      // 播放计划
      const handlePlayPlan = async () => {
        if (!refData.planStatus.value) {
          ElMessage.warning("请先选择一个计划");
          return;
        }
        try {
          refData.playing.value = true;
          const response = await axios.post(`${getApiUrl()}/plan/play`, {
            id: refData.activePlanId.value,
            force: false,
          });
          if (response.data && response.data.code === 0) {
            ElMessage.success("开始播放");
            await loadPlan(); // 刷新状态
          } else {
            ElMessage.error(response.data?.msg || "播放失败");
          }
        } catch (error) {
          console.error("播放失败:", error);
          ElMessage.error("播放失败: " + (error.message || "未知错误"));
        } finally {
          refData.playing.value = false;
        }
      };

      // 停止播放
      const handleStopPlan = async () => {
        if (!refData.planStatus.value) {
          return;
        }
        try {
          refData.stopping.value = true;
          const response = await axios.post(`${getApiUrl()}/plan/stop`, {
            id: refData.activePlanId.value,
          });
          if (response.data && response.data.code === 0) {
            ElMessage.success("已停止");
            await loadPlan(); // 刷新状态
          } else {
            ElMessage.error(response.data?.msg || "停止失败");
          }
        } catch (error) {
          console.error("停止失败:", error);
          ElMessage.error("停止失败: " + (error.message || "未知错误"));
        } finally {
          refData.stopping.value = false;
        }
      };

      // Cron 相关方法
      const updateCronExpression = () => {
        refData.cronBuilder.value.generated = generateCronExpression(refData.cronBuilder.value);
      };

      const handleOpenCronBuilder = () => {
        refData.cronBuilderVisible.value = true;
        const cronExpr = refData.planStatus.value?.schedule?.cron;
        if (cronExpr) {
          // 解析 cron 表达式（简化版，可以后续完善）
          // 这里先简单设置
        } else {
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
        }
      };

      const handleCloseCronBuilder = () => {
        refData.cronBuilderVisible.value = false;
      };

      const handleApplyCronExpression = async () => {
        if (!refData.cronBuilder.value.generated) return;
        const cronExpr = refData.cronBuilder.value.generated;
        await updateActivePlanData((planInfo) => {
          if (!planInfo.schedule) {
            planInfo.schedule = { enabled: 0, cron: "", duration: 0 };
          }
          planInfo.schedule.cron = cronExpr;
          return planInfo;
        });
        handleCloseCronBuilder();
        ElMessage.success("Cron 表达式已应用");
      };

      const handlePreviewGeneratedCron = () => {
        const cronExpr = refData.cronBuilder.value.generated;
        if (!cronExpr) {
          ElMessage.warning("请先生成 Cron 表达式");
          return;
        }
        try {
          const times = calculateNextCronTimes(cronExpr, 5);
          refData.cronPreviewTimes.value = times;
          refData.cronPreviewVisible.value = true;
        } catch (error) {
          ElMessage.error("预览失败: " + (error.message || "无效的 Cron 表达式"));
          refData.cronPreviewTimes.value = [];
        }
      };

      const handlePreviewPlanCron = () => {
        if (!refData.planStatus.value || !refData.planStatus.value.schedule?.cron) {
          ElMessage.warning("请先设置 Cron 表达式");
          return;
        }
        try {
          const cronExpr = refData.planStatus.value.schedule.cron;
          const times = calculateNextCronTimes(cronExpr, 5);
          if (times && times.length > 0) {
            refData.cronPreviewTimes.value = times;
            refData.cronPreviewVisible.value = true;
          } else {
            ElMessage.warning("无法解析 Cron 表达式");
          }
        } catch (error) {
          ElMessage.error("预览失败: " + error.message);
        }
      };

      // 切换计划 Cron 启用状态
      const handleTogglePlanCronEnabled = async (enabled) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (!planInfo.schedule) {
            planInfo.schedule = { enabled: 0, cron: "", duration: 0 };
          }
          planInfo.schedule.enabled = enabled ? 1 : 0;
          return planInfo;
        });
      };

      // 更新计划的 Cron 表达式
      const handleUpdatePlanCron = async (cron) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (!planInfo.schedule) {
            planInfo.schedule = { enabled: 0, cron: "", duration: 0 };
          }
          planInfo.schedule.cron = cron;
          return planInfo;
        });
      };

      // 更新计划的持续时间
      const handleUpdatePlanDuration = async (duration) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (!planInfo.schedule) {
            planInfo.schedule = { enabled: 0, cron: "", duration: 0 };
          }
          planInfo.schedule.duration = duration || 0;
          return planInfo;
        });
      };

      // 更新计划的设备类型
      const handleUpdatePlanDeviceType = async (deviceType) => {
        if (!refData.planStatus.value) return;
        const validDeviceTypes = ["agent", "dlna", "bluetooth", "mi"];
        if (!validDeviceTypes.includes(deviceType)) {
          ElMessage.error(`无效的设备类型: ${deviceType}`);
          return;
        }
        pendingDeviceType.value = deviceType;
        const status = refData.planStatus.value;
        status.device_type = deviceType;
        if (!status.device) {
          status.device = { type: deviceType, address: "", name: null };
        } else {
          status.device.type = deviceType;
        }
        await refreshConnectedList();
      };

      // 更新计划的设备地址
      const handleUpdatePlanDeviceAddress = async (address, name = null) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          const finalType =
            pendingDeviceType.value ||
            planInfo.device?.type ||
            planInfo.device_type ||
            "dlna";

          if (!planInfo.device) {
            planInfo.device = { address: "", type: finalType, name: null };
          }
          planInfo.device.type = finalType;
          planInfo.device.address = address;
          if (name !== null) {
            planInfo.device.name = name;
          }
          planInfo.device_address = address;
          planInfo.device_type = finalType;
          return planInfo;
        });
        pendingDeviceType.value = null;
      };

      // 刷新已连接设备列表
      const refreshConnectedList = async () => {
        if (!refData.planStatus.value) return;
        const deviceType = refData.planStatus.value.device?.type || refData.planStatus.value.device_type;
        if (!deviceType) return;

        try {
          refData.loading.value = true;
          if (deviceType === "bluetooth") {
            const response = await bluetoothAction("getPairedDevices", {});
            if (response.data && response.data.code === 0) {
              refData.connectedDeviceList.value = (response.data.data || []).map(d => ({
                address: d.address,
                name: d.name || d.address,
              }));
            }
          } else if (deviceType === "agent") {
            // 设备代理相关逻辑
            refData.connectedDeviceList.value = [];
          } else {
            refData.connectedDeviceList.value = [];
          }
        } catch (error) {
          console.error("刷新设备列表失败:", error);
        } finally {
          refData.loading.value = false;
        }
      };

      // 打开扫描对话框
      const handleOpenScanDialog = () => {
        refData.scanDialogVisible.value = true;
        refreshConnectedList();
      };

      // 选择设备
      const handleSelectDevice = async (device) => {
        await handleUpdatePlanDeviceAddress(device.address, device.name);
      };

      // 选择扫描到的设备
      const handleSelectScannedDevice = async (device) => {
        await handleUpdatePlanDeviceAddress(device.address, device.name);
        refData.scanDialogVisible.value = false;
      };

      // 获取计划的下次 Cron 运行时间
      const getPlanNextCronTime = (plan) => {
        if (
          !plan ||
          !plan.schedule ||
          plan.schedule.enabled !== 1 ||
          !plan.schedule.cron ||
          typeof plan.schedule.cron !== 'string'
        ) {
          return null;
        }
        try {
          const cronExpr = String(plan.schedule.cron).trim();
          if (!cronExpr) {
            return null;
          }
          const times = calculateNextCronTimes(cronExpr, 1);
          if (times && times.length > 0) {
            return times[0];
          }
          return null;
        } catch (error) {
          return null;
        }
      };

      // 监听活动计划ID变化
      watch(() => refData.activePlanId.value, (newId) => {
        if (newId) {
          syncActivePlan(refData.planCollection.value);
        }
      });

      // 初始化
      onMounted(async () => {
        await loadPlan();
      });

      return {
        ...refData,
        formatDuration,
        refreshPlanStatus,
        handleSelectPlan,
        handleCreatePlan,
        handlePlanMenuCommand,
        handleTogglePlanEnabled,
        handleStartEditPlanName,
        handleSavePlanName,
        handleCancelEditPlanName,
        handleAddPreList,
        handleDeletePreList,
        handleTogglePreListWeekday,
        handleOpenFileBrowserForPreList,
        handleOpenFileBrowserForMainList,
        handleCloseFileBrowser,
        handleFileSelected,
        handleDeletePreListFile,
        handleDeleteMainListFile,
        handlePlayPlan,
        handleStopPlan,
        updateCronExpression,
        handleOpenCronBuilder,
        handleCloseCronBuilder,
        handleApplyCronExpression,
        handlePreviewGeneratedCron,
        handlePreviewPlanCron,
        handleTogglePlanCronEnabled,
        handleUpdatePlanCron,
        handleUpdatePlanDuration,
        handleUpdatePlanDeviceType,
        handleUpdatePlanDeviceAddress,
        handleOpenScanDialog,
        handleSelectDevice,
        handleSelectScannedDevice,
        getPlanNextCronTime,
      };
    },
    template,
  };
  return component;
}

export default createComponent();

