import { bluetoothAction, getApiUrl } from "../js/net_util.js";
import { createPlaylistId, formatDuration, calculateNextCronTimes, generateCronExpression } from "../js/utils.js";
import { createFileDialog } from "./common/file_dialog.js";
const axios = window.axios;

const { ref, watch, onMounted } = window.Vue;
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
        selectedWeekday: ref(null), // 选中的星期几，null 表示使用当前日期
        preFilesDragMode: ref(false), // 前置文件拖拽排序模式
        mainFilesDragMode: ref(false), // 正式文件拖拽排序模式
        preFilesOriginalOrder: ref(null), // 前置文件原始顺序
        mainFilesOriginalOrder: ref(null), // 正式文件原始顺序
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
      const createDefaultPlan = (overrides = {}) => {
        // 确保有7个前置列表（周一到周日）
        let pre_lists = overrides.pre_lists || [];
        if (!Array.isArray(pre_lists) || pre_lists.length === 0) {
          pre_lists = Array(7).fill(null).map(() => ({ files: [] }));
        } else {
          // 确保有7个，不足的补齐
          while (pre_lists.length < 7) {
            pre_lists.push({ files: [] });
          }
          // 如果超过7个，只取前7个
          pre_lists = pre_lists.slice(0, 7);
        }
        return {
          id: overrides.id || createPlaylistId(),
          name: overrides.name || "默认计划",
          enabled: overrides.enabled || 0,
          pre_lists,
          main_list: overrides.main_list || { files: [] },
          device_address: overrides.device_address || null,
          device_type: overrides.device_type || "dlna",
          device: overrides.device || { type: "dlna", address: null, name: null },
          schedule: overrides.schedule || { enabled: 0, cron: "", duration: 0 },
        };
      };

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

        // 规范化前置列表，确保有7个（周一到周日，索引0-6对应星期1-7）
        let pre_lists = item?.pre_lists || [];
        if (!Array.isArray(pre_lists) || pre_lists.length === 0) {
          pre_lists = Array(7).fill(null).map(() => ({ files: [] }));
        } else {
          // 确保有7个，不足的补齐，超过的截取
          pre_lists = pre_lists.map(preList => ({
            files: normalizeFiles(preList?.files || []),
          }));
          while (pre_lists.length < 7) {
            pre_lists.push({ files: [] });
          }
          pre_lists = pre_lists.slice(0, 7);
        }

        return {
          id: item?.id || createPlaylistId(),
          name,
          enabled: item?.enabled || 0,
          pre_lists,
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

      // 保存/恢复选中的星期几
      const saveSelectedWeekday = (weekday) => {
        try {
          if (weekday !== null && weekday >= 1 && weekday <= 7) {
            localStorage.setItem('selected_weekday', String(weekday));
          } else {
            localStorage.removeItem('selected_weekday');
          }
        } catch (error) {
          console.warn("保存星期几失败:", error);
        }
      };

      const restoreSelectedWeekday = () => {
        try {
          const saved = localStorage.getItem('selected_weekday');
          if (saved) {
            const weekday = parseInt(saved, 10);
            if (weekday >= 1 && weekday <= 7) {
              return weekday;
            }
          }
          return null;
        } catch (error) {
          console.warn("恢复星期几失败:", error);
          return null;
        }
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
            
            // 恢复选中的星期几
            const savedWeekday = restoreSelectedWeekday();
            if (savedWeekday !== null) {
              refData.selectedWeekday.value = savedWeekday;
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
      // 改名计划（使用弹窗）
      const handleStartEditPlanName = async (planId) => {
        const plan = refData.planCollection.value.find(p => p.id === planId);
        if (!plan) return;
        
        try {
          const { value } = await ElMessageBox.prompt("请输入计划名称", "修改计划名称", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            inputValue: plan.name,
            inputPlaceholder: plan.name,
            inputValidator: (val) => (!!val && val.trim().length > 0) || "名称不能为空",
          });
          const newName = (value || plan.name).trim();
          
          await updateActivePlanData((planInfo) => {
            planInfo.name = newName;
            return planInfo;
          });
          
          // 更新 planCollection 中的名称
          const planIndex = refData.planCollection.value.findIndex(p => p.id === planId);
          if (planIndex >= 0) {
            refData.planCollection.value[planIndex].name = newName;
          }
          
          ElMessage.success("计划名称已修改");
        } catch (error) {
          if (error === "cancel") return;
          console.error("修改计划名称失败:", error);
          ElMessage.error("修改计划名称失败: " + (error.message || "未知错误"));
        }
      };

      const handleSavePlanName = async () => {
        // 已废弃，使用 handleStartEditPlanName 的弹窗方式
        // 保留函数以避免模板中的引用错误
      };

      const handleCancelEditPlanName = () => {
        // 已废弃，使用 handleStartEditPlanName 的弹窗方式
      };

      // 添加前置列表（打开文件对话框，添加到当前选中日期）
      const handleAddPreList = () => {
        if (!refData.planStatus.value) {
          ElMessage.warning("请先选择一个计划");
          return;
        }
        const currentWeekday = getCurrentWeekday();
        const preListIndex = currentWeekday - 1; // 星期1-7转换为索引0-6
        refData.fileBrowserDialogVisible.value = true;
        refData.fileBrowserTarget.value = `pre_list_${preListIndex}`; // 添加到对应日期的前置列表
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

      // 切换前置列表星期（已废弃，现在每个日期有固定的前置列表）
      const handleTogglePreListWeekday = async () => {
        // 此功能已废弃，保留函数以避免错误
        ElMessage.info("现在每个日期有固定的前置列表，无需切换星期");
      };

      // 打开文件浏览器（前置列表，preListIndex 是星期几 1-7）
      const handleOpenFileBrowserForPreList = (weekday) => {
        if (!refData.planStatus.value) return;
        const preListIndex = weekday - 1; // 星期1-7转换为索引0-6
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
              // 添加到指定日期的前置列表（索引0-6对应星期1-7）
              const preListIndex = parseInt(target.replace("pre_list_", ""));
              // 确保有7个前置列表
              if (!planInfo.pre_lists) {
                planInfo.pre_lists = Array(7).fill(null).map(() => ({ files: [] }));
              }
              while (planInfo.pre_lists.length < 7) {
                planInfo.pre_lists.push({ files: [] });
              }
              if (preListIndex >= 0 && preListIndex < 7) {
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
          const targetName = target === "main_list" ? "正式列表" : target === "new_pre_list" ? "前置列表" : "列表";
          ElMessage.success(`已添加 ${filePaths.length} 个文件到${targetName}`);
        } catch (error) {
          console.error("添加文件失败:", error);
          ElMessage.error("添加文件失败: " + (error.message || "未知错误"));
        } finally {
          refData.planLoading.value = false;
        }
      };

      // 删除前置列表文件（preListIndex 是星期几 1-7）
      const handleDeletePreListFile = async (weekday, fileIndex) => {
        if (!refData.planStatus.value) return;
        await updateActivePlanData((planInfo) => {
          if (!planInfo.pre_lists) {
            planInfo.pre_lists = Array(7).fill(null).map(() => ({ files: [] }));
          }
          while (planInfo.pre_lists.length < 7) {
            planInfo.pre_lists.push({ files: [] });
          }
          const preListIndex = weekday - 1; // 星期1-7转换为索引0-6
          if (preListIndex >= 0 && preListIndex < 7 && planInfo.pre_lists[preListIndex] && planInfo.pre_lists[preListIndex].files) {
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

      // 清空前置列表（当前选中星期几的前置列表文件）
      const handleClearPreLists = async () => {
        if (!refData.planStatus.value) return;
        const weekday = getCurrentWeekday();
        const preListIndex = weekday - 1; // 星期1-7转换为索引0-6
        const fileCount = getPreListFileCountForWeekday(weekday);
        
        if (fileCount === 0) {
          ElMessage.info("当前日期无前置列表文件");
          return;
        }

        try {
          await ElMessageBox.confirm(
            `确定要清空当前日期（${['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][weekday]}）的前置列表文件吗？此操作将删除 ${fileCount} 个文件。`,
            "确认清空",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              type: "warning",
            }
          );

          await updateActivePlanData((planInfo) => {
            if (!planInfo.pre_lists) {
              planInfo.pre_lists = Array(7).fill(null).map(() => ({ files: [] }));
            }
            while (planInfo.pre_lists.length < 7) {
              planInfo.pre_lists.push({ files: [] });
            }
            if (preListIndex >= 0 && preListIndex < 7) {
              planInfo.pre_lists[preListIndex].files = [];
            }
            return planInfo;
          });
          ElMessage.success("已清空前置列表文件");
        } catch (error) {
          if (error !== "cancel") {
            console.error("清空失败:", error);
            ElMessage.error("清空失败: " + (error.message || "未知错误"));
          }
        }
      };

      // 清空正式列表
      const handleClearMainList = async () => {
        if (!refData.planStatus.value) return;
        const filesCount = (refData.planStatus.value.main_list?.files?.length || 0);
        
        if (filesCount === 0) {
          ElMessage.info("正式列表已为空");
          return;
        }

        try {
          await ElMessageBox.confirm(
            `确定要清空正式列表吗？此操作将删除所有 ${filesCount} 个文件。`,
            "确认清空",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              type: "warning",
            }
          );

          await updateActivePlanData((planInfo) => {
            if (planInfo.main_list) {
              planInfo.main_list.files = [];
            }
            return planInfo;
          });
          ElMessage.success("已清空正式列表");
        } catch (error) {
          if (error !== "cancel") {
            console.error("清空失败:", error);
            ElMessage.error("清空失败: " + (error.message || "未知错误"));
          }
        }
      };

      // 检查两个数组的顺序是否相同
      const isOrderChanged = (original, current) => {
        if (!original || !current || original.length !== current.length) {
          return true;
        }
        for (let i = 0; i < original.length; i++) {
          const origUri = original[i]?.uri || original[i];
          const currUri = current[i]?.uri || current[i];
          if (origUri !== currUri) {
            return true;
          }
        }
        return false;
      };

      // 切换前置文件拖拽排序模式
      const handleTogglePreFilesDragMode = async () => {
        if (refData.preFilesDragMode.value) {
          // 退出拖拽模式时，检查是否有变化
          const currentWeekday = getCurrentWeekday();
          const preListIndex = currentWeekday - 1;
          const preList = refData.planStatus.value?.pre_lists?.[preListIndex];
          if (preList && preList.files && preList.files.length > 0) {
            const hasChanged = isOrderChanged(refData.preFilesOriginalOrder.value, preList.files);
            if (hasChanged) {
              try {
                refData.planLoading.value = true;
                await updateActivePlanData((planInfo) => {
                  // 使用当前内存中的顺序
                  if (planInfo.pre_lists && planInfo.pre_lists[preListIndex]) {
                    planInfo.pre_lists[preListIndex].files = [...(preList.files || [])];
                  }
                  return planInfo;
                });
                ElMessage.success("排序已保存");
              } catch (error) {
                console.error("保存排序失败:", error);
                ElMessage.error("保存排序失败: " + (error.message || "未知错误"));
              } finally {
                refData.planLoading.value = false;
              }
            }
            // 清除原始顺序
            refData.preFilesOriginalOrder.value = null;
          }
        } else {
          // 启用拖拽模式时，保存原始顺序
          const currentWeekday = getCurrentWeekday();
          const preListIndex = currentWeekday - 1;
          const preList = refData.planStatus.value?.pre_lists?.[preListIndex];
          if (preList && preList.files && preList.files.length > 0) {
            refData.preFilesOriginalOrder.value = [...(preList.files || [])];
          }
        }
        refData.preFilesDragMode.value = !refData.preFilesDragMode.value;
      };

      // 切换正式文件拖拽排序模式
      const handleToggleMainFilesDragMode = async () => {
        if (refData.mainFilesDragMode.value) {
          // 退出拖拽模式时，检查是否有变化
          const mainList = refData.planStatus.value?.main_list;
          if (mainList && mainList.files && mainList.files.length > 0) {
            const hasChanged = isOrderChanged(refData.mainFilesOriginalOrder.value, mainList.files);
            if (hasChanged) {
              try {
                refData.planLoading.value = true;
                await updateActivePlanData((planInfo) => {
                  // 使用当前内存中的顺序
                  if (planInfo.main_list) {
                    planInfo.main_list.files = [...(mainList.files || [])];
                  }
                  return planInfo;
                });
                ElMessage.success("排序已保存");
              } catch (error) {
                console.error("保存排序失败:", error);
                ElMessage.error("保存排序失败: " + (error.message || "未知错误"));
              } finally {
                refData.planLoading.value = false;
              }
            }
            // 清除原始顺序
            refData.mainFilesOriginalOrder.value = null;
          }
        } else {
          // 启用拖拽模式时，保存原始顺序
          const mainList = refData.planStatus.value?.main_list;
          if (mainList && mainList.files && mainList.files.length > 0) {
            refData.mainFilesOriginalOrder.value = [...(mainList.files || [])];
          }
        }
        refData.mainFilesDragMode.value = !refData.mainFilesDragMode.value;
      };

      // 处理前置文件拖拽开始
      const handlePreFileDragStart = (event, fileIndex) => {
        if (!refData.preFilesDragMode.value) {
          event.preventDefault();
          return false;
        }
        try {
          event.dataTransfer.effectAllowed = 'move';
          event.dataTransfer.setData('text/plain', fileIndex.toString());
        } catch (e) {
          console.error('拖拽开始失败:', e);
        }
      };

      // 处理前置文件拖拽结束
      const handlePreFileDragEnd = (event) => {
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
      };

      // 处理前置文件拖拽悬停
      const handlePreFileDragOver = (event) => {
        if (!refData.preFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        if (event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          const mouseY = event.clientY;
          const elementCenterY = rect.top + rect.height / 2;
          
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
          
          if (mouseY < elementCenterY) {
            event.currentTarget.style.borderTop = '2px solid #3b82f6';
          } else {
            event.currentTarget.style.borderBottom = '2px solid #3b82f6';
          }
        }
      };

      // 处理前置文件拖拽放置
      const handlePreFileDrop = (event, targetIndex) => {
        if (!refData.preFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
        
        const sourceIndex = parseInt(event.dataTransfer.getData('text/plain'), 10);
        if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
          return;
        }

        const currentWeekday = getCurrentWeekday();
        const preListIndex = currentWeekday - 1;
        const preList = refData.planStatus.value?.pre_lists?.[preListIndex];
        if (!preList || !preList.files || sourceIndex < 0 || sourceIndex >= preList.files.length ||
            targetIndex < 0 || targetIndex >= preList.files.length) {
          return;
        }

        // 只在内存中更新，不保存到后端
        const list = [...(preList.files || [])];
        const [removed] = list.splice(sourceIndex, 1);
        list.splice(targetIndex, 0, removed);
        
        // 更新 planStatus
        refData.planStatus.value.pre_lists[preListIndex].files = list;
        
        // 更新 planCollection
        const collection = refData.planCollection.value.map(item => {
          if (item.id === refData.activePlanId.value) {
            const updatedPreLists = [...(item.pre_lists || [])];
            updatedPreLists[preListIndex] = { ...updatedPreLists[preListIndex], files: list };
            return { ...item, pre_lists: updatedPreLists };
          }
          return item;
        });
        refData.planCollection.value = collection;
        syncActivePlan(collection);
      };

      // 处理正式文件拖拽开始
      const handleMainFileDragStart = (event, fileIndex) => {
        if (!refData.mainFilesDragMode.value) {
          event.preventDefault();
          return false;
        }
        try {
          event.dataTransfer.effectAllowed = 'move';
          event.dataTransfer.setData('text/plain', fileIndex.toString());
        } catch (e) {
          console.error('拖拽开始失败:', e);
        }
      };

      // 处理正式文件拖拽结束
      const handleMainFileDragEnd = (event) => {
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
      };

      // 处理正式文件拖拽悬停
      const handleMainFileDragOver = (event) => {
        if (!refData.mainFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        if (event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          const mouseY = event.clientY;
          const elementCenterY = rect.top + rect.height / 2;
          
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
          
          if (mouseY < elementCenterY) {
            event.currentTarget.style.borderTop = '2px solid #3b82f6';
          } else {
            event.currentTarget.style.borderBottom = '2px solid #3b82f6';
          }
        }
      };

      // 处理正式文件拖拽放置
      const handleMainFileDrop = (event, targetIndex) => {
        if (!refData.mainFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
        
        const sourceIndex = parseInt(event.dataTransfer.getData('text/plain'), 10);
        if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
          return;
        }

        const mainList = refData.planStatus.value?.main_list;
        if (!mainList || !mainList.files || sourceIndex < 0 || sourceIndex >= mainList.files.length ||
            targetIndex < 0 || targetIndex >= mainList.files.length) {
          return;
        }

        // 只在内存中更新，不保存到后端
        const list = [...(mainList.files || [])];
        const [removed] = list.splice(sourceIndex, 1);
        list.splice(targetIndex, 0, removed);
        
        // 计算新的 file_index
        let newFileIndex = refData.planStatus.value.file_index;
        if (refData.planStatus.value.file_index !== undefined && refData.planStatus.value.file_index !== null && refData.planStatus.value.file_index >= 0) {
          if (refData.planStatus.value.file_index === sourceIndex) {
            newFileIndex = targetIndex;
          } else if (sourceIndex < refData.planStatus.value.file_index && targetIndex >= refData.planStatus.value.file_index) {
            newFileIndex = refData.planStatus.value.file_index - 1;
          } else if (sourceIndex > refData.planStatus.value.file_index && targetIndex <= refData.planStatus.value.file_index) {
            newFileIndex = refData.planStatus.value.file_index + 1;
          }
        }
        
        // 更新 planStatus
        refData.planStatus.value.main_list.files = list;
        refData.planStatus.value.file_index = newFileIndex;
        
        // 更新 planCollection
        const collection = refData.planCollection.value.map(item => {
          if (item.id === refData.activePlanId.value) {
            return { ...item, main_list: { files: list } };
          }
          return item;
        });
        refData.planCollection.value = collection;
        syncActivePlan(collection);
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

      // 获取当前星期几（1-7，周一=1，周日=7）
      const getCurrentWeekday = () => {
        if (refData.selectedWeekday.value !== null) {
          return refData.selectedWeekday.value;
        }
        const today = new Date();
        const weekday = today.getDay(); // 0=周日, 1=周一, ..., 6=周六
        return weekday === 0 ? 7 : weekday; // 转换为 1-7（周一=1，周日=7）
      };

      // 获取指定星期几的前置列表（索引0-6对应星期1-7）
      const getActivePreListsForWeekday = (weekday) => {
        if (!refData.planStatus.value || !refData.planStatus.value.pre_lists) {
          return [];
        }
        const preListIndex = weekday - 1; // 星期1-7转换为索引0-6
        if (preListIndex >= 0 && preListIndex < refData.planStatus.value.pre_lists.length) {
          const preList = refData.planStatus.value.pre_lists[preListIndex];
          return preList && preList.files && preList.files.length > 0 ? [preList] : [];
        }
        return [];
      };

      // 获取指定星期几的前置列表文件总数（索引0-6对应星期1-7）
      const getPreListFileCountForWeekday = (weekday) => {
        if (!refData.planStatus.value || !refData.planStatus.value.pre_lists) {
          return 0;
        }
        const preListIndex = weekday - 1; // 星期1-7转换为索引0-6
        if (preListIndex >= 0 && preListIndex < refData.planStatus.value.pre_lists.length) {
          const preList = refData.planStatus.value.pre_lists[preListIndex];
          return preList?.files?.length || 0;
        }
        return 0;
      };

      // 判断文件是否正在播放（用于前置列表，weekday 是星期几 1-7）
      const isPreListFilePlaying = (weekday, fileIndex) => {
        if (!refData.planStatus.value || !refData.planStatus.value.in_pre_files) {
          return false;
        }
        // 现在每个日期只有一个前置列表，直接比较索引
        const currentWeekday = getCurrentWeekday();
        if (weekday !== currentWeekday) {
          return false;
        }
        // 检查是否正在播放当前日期的前置列表，且文件索引匹配
        // pre_list_index 应该对应星期几的索引（0-6对应星期1-7）
        const preListIndex = weekday - 1;
        if (refData.planStatus.value.pre_list_index === preListIndex && 
            refData.planStatus.value.file_index === fileIndex) {
          return true;
        }
        return false;
      };

      // 选择星期几
      const handleSelectWeekday = (day) => {
        const currentWeekday = getCurrentWeekday();
        if (day === currentWeekday && refData.selectedWeekday.value === null) {
          // 如果点击的是当前日期且没有手动选择，则不做任何操作
          return;
        }
        refData.selectedWeekday.value = day;
        saveSelectedWeekday(day); // 保存到本地存储
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
        handleClearPreLists,
        handleClearMainList,
        handleTogglePreFilesDragMode,
        handleToggleMainFilesDragMode,
        handlePreFileDragStart,
        handlePreFileDragEnd,
        handlePreFileDragOver,
        handlePreFileDrop,
        handleMainFileDragStart,
        handleMainFileDragEnd,
        handleMainFileDragOver,
        handleMainFileDrop,
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
        getCurrentWeekday,
        getActivePreListsForWeekday,
        getPreListFileCountForWeekday,
        handleSelectWeekday,
        isPreListFilePlaying,
      };
    },
    template,
  };
  return component;
}

export default createComponent();

