import { bluetoothAction, getRdsData, setRdsData, playlistAction } from "../js/net_util.js";

const { ref, onMounted, nextTick, watch } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;
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
        fileBrowserDialogVisible: ref(false),
        fileBrowserPath: ref("/mnt"),
        fileBrowserList: ref([]),
        fileBrowserLoading: ref(false),
        selectedFiles: ref([]),
        cronExpression: ref(""),
        cronEnabled: ref(false),
        cronDuration: ref(0),
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
        playing: ref(false),
        stopping: ref(false),
        // 播放列表相关
        playlistCollection: ref([]),
        activePlaylistId: ref(""),
        playlistStatus: ref(null),
        playlistLoading: ref(false),
        playlistRefreshing: ref(false),
      };

      const RDS_TABLE = "schedule_play";
      const RDS_CRON_KEY = "cron_config";

      const saveCronConfigToRds = async () => {
        try {
          const cronConfig = {
            enabled: refData.cronEnabled.value,
            expression: refData.cronExpression.value,
            durationMinutes: refData.cronDuration.value,
            updatedAt: Date.now(),
          };
          await setRdsData(RDS_TABLE, RDS_CRON_KEY, JSON.stringify(cronConfig));
        } catch (error) {
          console.error("保存 Cron 配置到 RDS 失败:", error);
        }
      };

      const createPlaylistId = () => `pl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;

      const createDefaultPlaylist = (overrides = {}) => ({
        id: overrides.id || createPlaylistId(),
        name: overrides.name || "默认播放列表",
        playlist: overrides.playlist || [],
        current_index: overrides.current_index || 0,
        device_address: overrides.device_address || null,
      });

      const normalizePlaylistItem = (item, fallbackName = "播放列表") => {
        const playlist = Array.isArray(item?.playlist) ? [...item.playlist] : [];
        let currentIndex = typeof item?.current_index === "number" ? item.current_index : 0;
        if (playlist.length === 0) {
          currentIndex = 0;
        } else {
          if (currentIndex < 0) currentIndex = 0;
          if (currentIndex >= playlist.length) currentIndex = playlist.length - 1;
        }
        const name = (item?.name && String(item.name).trim()) || fallbackName;
        return {
          id: item?.id || createPlaylistId(),
          name,
          playlist,
          total: playlist.length,
          current_index: currentIndex,
          device_address: item?.device_address || null,
          updatedAt: item?.updatedAt || Date.now(),
        };
      };

      const normalizePlaylistCollection = (raw) => {
        const ensureList = (list) => {
          if (!Array.isArray(list) || list.length === 0) {
            return [normalizePlaylistItem(createDefaultPlaylist())];
          }
          return list.map((item, index) => normalizePlaylistItem(item, item?.name || `播放列表${index + 1}`));
        };

        if (raw && Array.isArray(raw.playlists)) {
          const playlists = ensureList(raw.playlists);
          const activeId = playlists.some((item) => item.id === raw.activePlaylistId)
            ? raw.activePlaylistId
            : playlists[0].id;
          return { playlists, activePlaylistId: activeId };
        }

        if (raw && Array.isArray(raw.playlist)) {
          const migrated = normalizePlaylistItem({
            id: raw.id || raw.playlist_id,
            name: raw.name || "默认播放列表",
            playlist: raw.playlist,
            current_index: raw.current_index,
            device_address: raw.device_address,
          });
          return { playlists: [migrated], activePlaylistId: migrated.id };
        }

        const defaultPlaylist = normalizePlaylistItem(createDefaultPlaylist());
        return { playlists: [defaultPlaylist], activePlaylistId: defaultPlaylist.id };
      };

      const syncActivePlaylist = (collection) => {
        const list = Array.isArray(collection) ? collection : refData.playlistCollection.value;
        if (!list || list.length === 0) {
          refData.playlistStatus.value = null;
          refData.activePlaylistId.value = "";
          return;
        }
        let activeId = refData.activePlaylistId.value;
        let active = list.find((item) => item.id === activeId);
        if (!active) {
          active = list[0];
          activeId = active.id;
        }
        refData.activePlaylistId.value = activeId;
        refData.playlistStatus.value = {
          ...active,
          playlist: [...(active.playlist || [])],
        };
      };

      const savePlaylistCollectionToApi = async (collectionOverride) => {
        try {
          const collection = (collectionOverride || refData.playlistCollection.value || []).map((item) => ({
            ...item,
            total: Array.isArray(item.playlist) ? item.playlist.length : 0,
            updatedAt: Date.now(),
          }));
          
          // 转换为后端期望的格式：字典格式，key 是播放列表 id
          const playlistDict = {};
          collection.forEach(item => {
            if (item.id) {
              playlistDict[item.id] = {
                id: item.id,
                name: item.name || "默认播放列表",
                files: item.playlist || [],
                current_index: item.current_index || 0,
                device: item.device || { address: item.device_address || "", type: item.device_type || "" },
                schedule: item.schedule || { enabled: 0, cron: "", duration: 0 },
                create_time: item.create_time || new Date().toISOString(),
                updated_time: new Date().toISOString(),
              };
            }
          });
          
          // 通过接口保存
          const response = await playlistAction("update", "POST", playlistDict);
          if (response.code !== 0) {
            throw new Error(response.msg || "保存播放列表失败");
          }
        } catch (error) {
          console.error("保存播放列表到接口失败:", error);
        }
      };

      // 保持向后兼容的函数名
      const savePlaylistCollectionToRds = savePlaylistCollectionToApi;

      const loadPlaylistFromApi = async () => {
        try {
          // 从接口获取播放列表
          const response = await playlistAction("get", "GET", {});
          if (response.code !== 0) {
            throw new Error(response.msg || "获取播放列表失败");
          }
          
          // 接口返回的数据格式：{ code: 0, msg: "ok", data: {...} }
          // data 是字典格式（所有播放列表，key 是 id），例如：{ "pl_123": {...}, "pl_456": {...} }
          const apiData = response.data;
          
          // 转换数据格式以适配 normalizePlaylistCollection
          let parsed = null;
          if (apiData && typeof apiData === 'object') {
            // 如果返回的是字典格式（多个播放列表，key 是 id）
            if (!Array.isArray(apiData) && Object.keys(apiData).length > 0) {
              // 将字典转换为数组，并转换字段名
              const playlists = Object.values(apiData).map(item => ({
                id: item.id,
                name: item.name || "默认播放列表",
                playlist: item.files || [],  // 后端使用 files，前端使用 playlist
                current_index: item.current_index || 0,
                device_address: item.device?.address || null,
                device_type: item.device?.type || null,
                device: item.device || {},
                schedule: item.schedule || { enabled: 0, cron: "", duration: 0 },
                create_time: item.create_time,
                updated_time: item.updated_time,
                updatedAt: item.updated_time ? new Date(item.updated_time).getTime() : Date.now(),
              }));
              
              parsed = {
                playlists: playlists,
                activePlaylistId: playlists[0]?.id || null
              };
            }
            // 如果返回的是数组
            else if (Array.isArray(apiData)) {
              parsed = {
                playlists: apiData.map(item => ({
                  ...item,
                  playlist: item.files || item.playlist || [],
                })),
                activePlaylistId: apiData[0]?.id || null
              };
            }
            // 如果返回的是单个播放列表对象
            else if (apiData.id) {
              parsed = {
                playlists: [{
                  ...apiData,
                  playlist: apiData.files || apiData.playlist || [],
                }],
                activePlaylistId: apiData.id
              };
            }
          }
          
          const normalized = normalizePlaylistCollection(parsed);
          refData.playlistCollection.value = normalized.playlists;
          refData.activePlaylistId.value = normalized.activePlaylistId;
          syncActivePlaylist(normalized.playlists);
          return normalized;
        } catch (error) {
          console.error("从接口加载播放列表失败:", error);
          const fallback = normalizePlaylistCollection(null);
          refData.playlistCollection.value = fallback.playlists;
          refData.activePlaylistId.value = fallback.activePlaylistId;
          syncActivePlaylist(fallback.playlists);
          return fallback;
        }
      };

      // 保持向后兼容的函数名
      const loadPlaylistFromRds = loadPlaylistFromApi;

      const updateActivePlaylistData = async (mutator) => {
        if (typeof mutator !== "function") return null;
        let collection = refData.playlistCollection.value.map((item) => ({
          ...item,
          playlist: Array.isArray(item.playlist) ? [...item.playlist] : [],
        }));
        if (collection.length === 0) {
          const defaultPlaylist = normalizePlaylistItem(createDefaultPlaylist());
          collection = [defaultPlaylist];
          refData.activePlaylistId.value = defaultPlaylist.id;
        }
        let index = collection.findIndex((item) => item.id === refData.activePlaylistId.value);
        if (index === -1) {
          index = 0;
          refData.activePlaylistId.value = collection[0].id;
        }
        const currentItem = collection[index];
        const updatedItem = mutator({
          ...currentItem,
          playlist: [...currentItem.playlist],
        }) || currentItem;
        collection[index] = normalizePlaylistItem(updatedItem, currentItem.name);
        refData.playlistCollection.value = collection;
        await savePlaylistCollectionToRds(collection, refData.activePlaylistId.value);
        syncActivePlaylist(collection);
        return refData.playlistStatus.value;
      };

      const loadCronConfigFromRds = async () => {
        try {
          const dataStr = await getRdsData(RDS_TABLE, RDS_CRON_KEY);
          if (!dataStr) return;
          const data = JSON.parse(dataStr);
          if (typeof data.enabled === "boolean") {
            refData.cronEnabled.value = data.enabled;
          }
          if (typeof data.expression === "string" && data.expression.trim().length > 0) {
            refData.cronExpression.value = data.expression;
          }
          if (data.durationMinutes !== undefined && data.durationMinutes !== null) {
            refData.cronDuration.value = parseInt(data.durationMinutes, 10) || 0;
          }
          updateNextRunTime();
        } catch (error) {
          console.error("从 RDS 加载 Cron 配置失败:", error);
        }
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
          const parts = cronExpr.trim().split(/\s+/);
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
            
            // 立即更新生成的表达式
            updateCronExpression();
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
        
      };

      // 保存配置
      const saveBluetoothConfig = async () => {
        try {
          await saveCronConfigToRds();
          ElMessage.success("Cron 配置已保存");
        } catch (error) {
          console.error("保存配置失败:", error);
          ElMessage.error("保存配置失败: " + (error.message || "未知错误"));
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
        if (!refData.cronBuilder.value.generated) return;
        refData.cronExpression.value = refData.cronBuilder.value.generated;
        handleCloseCronBuilder();
        updateNextRunTime();
        saveBluetoothConfig();
        ElMessage.success("Cron 表达式已应用");
      };

      // 切换 Cron 启用状态
      const handleToggleCronEnabled = async () => {
        // 立即保存配置
        await saveBluetoothConfig();
      };

      // 应用示例
      const applyExample = (example) => {
        try {
          parseCronExpression(example);
          nextTick(() => {
            if (refData.cronBuilder.value.generated) {
              refData.cronExpression.value = refData.cronBuilder.value.generated;
              updateNextRunTime();
              saveBluetoothConfig();
              ElMessage.success("示例已应用");
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
          const times = calculateNextCronTimes(cronExpr, 5);
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
          const times = calculateNextCronTimes(refData.cronExpression.value, 5);
          refData.cronPreviewTimes.value = times;
          refData.cronPreviewVisible.value = true;
        } catch (error) {
          ElMessage.error("预览失败: " + (error.message || "无效的 Cron 表达式"));
          refData.cronPreviewTimes.value = [];
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

      // 格式化持续时间（分钟转换为可读格式）
      const formatDurationMinutes = (minutes) => {
        if (!minutes || minutes === 0) return "不停止";
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        
        const parts = [];
        if (hours > 0) {
          parts.push(`${hours}小时`);
        }
        if (mins > 0) {
          parts.push(`${mins}分钟`);
        }
        
        return parts.length > 0 ? parts.join(" ") : "0分钟";
      };



      // ========== 播放列表管理功能 ==========
      
      // 刷新播放列表状态
      const refreshPlaylistStatus = async () => {
        try {
          refData.playlistRefreshing.value = true;
          await loadPlaylistFromRds();
        } catch (error) {
          console.error("刷新播放列表状态失败:", error);
        } finally {
          refData.playlistRefreshing.value = false;
        }
      };

      // 播放播放列表
      const handlePlayPlaylist = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || status.playlist.length === 0) {
          ElMessage.warning("播放列表为空，请先添加文件");
          return;
        }
        try {
          refData.playing.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = Array.isArray(playlistInfo.playlist) ? playlistInfo.playlist : [];
            playlistInfo.current_index = Math.max(0, Math.min(playlistInfo.current_index || 0, list.length - 1));
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("播放状态已保存");
        } catch (error) {
          console.error("播放失败:", error);
          ElMessage.error("播放失败: " + (error.message || "未知错误"));
        } finally {
          refData.playing.value = false;
        }
      };

      // 播放下一首
      const handlePlayNext = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || status.playlist.length === 0) {
          ElMessage.warning("播放列表为空，无法播放下一首");
          return;
        }
        try {
          refData.playing.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = Array.isArray(playlistInfo.playlist) ? playlistInfo.playlist : [];
            if (list.length === 0) return playlistInfo;
            const nextIndex = (playlistInfo.current_index + 1) % list.length;
            playlistInfo.current_index = nextIndex;
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("已切换到下一首");
        } catch (error) {
          console.error("播放下一首失败:", error);
          ElMessage.error("播放下一首失败: " + (error.message || "未知错误"));
        } finally {
          refData.playing.value = false;
        }
      };

      // 停止播放列表
      const handleStopPlaylist = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || status.playlist.length === 0) {
          ElMessage.warning("播放列表为空");
          return;
        }
        try {
          refData.stopping.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            playlistInfo.current_index = 0;
            return playlistInfo;
          });
          ElMessage.success("播放状态已停止（本地记录）");
        } catch (error) {
          console.error("停止播放列表失败:", error);
          ElMessage.error("停止播放列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.stopping.value = false;
        }
      };

      // 获取当前播放文件名称
      const getCurrentPlaylistFile = () => {
        if (!refData.playlistStatus.value) return null;
        const playlist = refData.playlistStatus.value.playlist || [];
        const currentIndexRaw = refData.playlistStatus.value.current_index;
        const currentIndex = typeof currentIndexRaw === "number" ? currentIndexRaw : 0;
        if (playlist.length === 0) return null;
        if (currentIndex >= 0 && currentIndex < playlist.length) {
          const filePath = playlist[currentIndex];
          // 只返回文件名，不包含路径
          return filePath.split('/').pop() || filePath;
        }
        return null;
      };

      // ========== 播放列表管理功能（调整顺序、删除） ==========
      
      // 上移播放列表项
      const handleMovePlaylistItemUp = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index <= 0 || index >= status.playlist.length) return;
        
        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...playlistInfo.playlist];
            [list[index - 1], list[index]] = [list[index], list[index - 1]];
            playlistInfo.playlist = list;
            if (playlistInfo.current_index === index) {
              playlistInfo.current_index = index - 1;
            } else if (playlistInfo.current_index === index - 1) {
              playlistInfo.current_index = index;
            }
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("已上移");
        } catch (error) {
          console.error("上移失败:", error);
          ElMessage.error("上移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 下移播放列表项
      const handleMovePlaylistItemDown = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index < 0 || index >= status.playlist.length - 1) return;
        
        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...playlistInfo.playlist];
            [list[index], list[index + 1]] = [list[index + 1], list[index]];
            playlistInfo.playlist = list;
            if (playlistInfo.current_index === index) {
              playlistInfo.current_index = index + 1;
            } else if (playlistInfo.current_index === index + 1) {
              playlistInfo.current_index = index;
            }
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("已下移");
        } catch (error) {
          console.error("下移失败:", error);
          ElMessage.error("下移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 删除播放列表项
      const handleDeletePlaylistItem = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index < 0 || index >= status.playlist.length) return;
        
        const fileName = status.playlist[index].split('/').pop() || status.playlist[index];
        
        try {
          await ElMessageBox.confirm(
            `确定要删除 "${fileName}" 吗？`,
            '确认删除',
            {
              confirmButtonText: '确定',
              cancelButtonText: '取消',
              type: 'warning',
            }
          );
          
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...playlistInfo.playlist];
            list.splice(index, 1);
            playlistInfo.playlist = list;
            if (list.length === 0) {
              playlistInfo.current_index = 0;
            } else if (index < playlistInfo.current_index) {
              playlistInfo.current_index = Math.max(0, playlistInfo.current_index - 1);
            } else if (index === playlistInfo.current_index) {
              playlistInfo.current_index = Math.min(playlistInfo.current_index, list.length - 1);
            }
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("已删除");
        } catch (error) {
          if (error !== 'cancel') {
            console.error("删除失败:", error);
            ElMessage.error("删除失败: " + (error.message || "未知错误"));
          }
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      const handleSelectPlaylist = async (playlistId) => {
        if (!playlistId || playlistId === refData.activePlaylistId.value) return;
        const exists = refData.playlistCollection.value.find((item) => item.id === playlistId);
        if (!exists) return;
        refData.activePlaylistId.value = playlistId;
        syncActivePlaylist(refData.playlistCollection.value);
        try {
          await savePlaylistCollectionToRds();
        } catch (error) {
          console.error("切换播放列表失败:", error);
        }
      };

      const handleCreatePlaylist = async () => {
        try {
          const defaultName = `播放列表${refData.playlistCollection.value.length + 1}`;
          const { value } = await ElMessageBox.prompt(
            "请输入播放列表名称",
            "新建播放列表",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              inputValue: defaultName,
              inputPlaceholder: defaultName,
              inputValidator: (val) => (!!val && val.trim().length > 0) || "名称不能为空",
            }
          );
          const playlistName = (value || defaultName).trim();
          const newPlaylist = normalizePlaylistItem({
            id: createPlaylistId(),
            name: playlistName,
            playlist: [],
            current_index: 0,
            device_address: null,
          }, playlistName);
          const updated = [...refData.playlistCollection.value, newPlaylist];
          refData.playlistCollection.value = updated;
          refData.activePlaylistId.value = newPlaylist.id;
          syncActivePlaylist(updated);
          await savePlaylistCollectionToRds(updated, newPlaylist.id);
          ElMessage.success("播放列表已创建");
        } catch (error) {
          if (error === 'cancel') return;
          console.error("创建播放列表失败:", error);
          ElMessage.error("创建播放列表失败: " + (error.message || "未知错误"));
        }
      };

      const handleDeletePlaylistGroup = async (playlistId) => {
        if (!playlistId) return;
        if (refData.playlistCollection.value.length <= 1) {
          ElMessage.warning("至少保留一个播放列表");
          return;
        }
        const target = refData.playlistCollection.value.find((item) => item.id === playlistId);
        if (!target) return;
        try {
          await ElMessageBox.confirm(
            `确认删除播放列表“${target.name}”吗？`,
            "删除播放列表",
            {
              confirmButtonText: "删除",
              cancelButtonText: "取消",
              type: "warning",
            }
          );
          const updated = refData.playlistCollection.value.filter((item) => item.id !== playlistId);
          refData.playlistCollection.value = updated;
          if (playlistId === refData.activePlaylistId.value) {
            refData.activePlaylistId.value = updated[0]?.id || "";
          }
          syncActivePlaylist(updated);
          await savePlaylistCollectionToRds(updated);
          ElMessage.success("播放列表已删除");
        } catch (error) {
          if (error === 'cancel') return;
          console.error("删除播放列表失败:", error);
          ElMessage.error("删除播放列表失败: " + (error.message || "未知错误"));
        }
      };

      // ========== 文件浏览和添加到播放列表功能 ==========
      
      // 打开文件浏览对话框
      const handleOpenFileBrowser = () => {
        if (!refData.playlistStatus.value) {
          ElMessage.warning("请先选择一个播放列表");
          return;
        }
        refData.fileBrowserDialogVisible.value = true;
        refData.fileBrowserPath.value = "/mnt";
        refData.selectedFiles.value = [];
        handleRefreshFileBrowser();
      };

      // 关闭文件浏览对话框
      const handleCloseFileBrowser = () => {
        refData.fileBrowserDialogVisible.value = false;
        refData.selectedFiles.value = [];
      };

      // 刷新文件浏览器列表
      const handleRefreshFileBrowser = async () => {
        try {
          refData.fileBrowserLoading.value = true;
          const path = refData.fileBrowserPath.value || "/mnt";
          const rsp = await bluetoothAction("listDirectory", "GET", {
            path: path,
          });
          if (rsp.code === 0) {
            refData.fileBrowserList.value = rsp.data || [];
            updateFileBrowserCanNavigateUp();
          } else {
            ElMessage.error(rsp.msg || "获取文件列表失败");
          }
        } catch (error) {
          console.error("获取文件列表失败:", error);
          ElMessage.error("获取文件列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.fileBrowserLoading.value = false;
        }
      };

      // 文件浏览器导航到上一级
      const handleFileBrowserNavigateUp = () => {
        const path = refData.fileBrowserPath.value;
        if (path && path !== "/mnt" && path !== "/") {
          const parts = path.split("/").filter(p => p);
          parts.pop();
          refData.fileBrowserPath.value = parts.length > 0 ? "/" + parts.join("/") : "/mnt";
          updateFileBrowserCanNavigateUp();
          handleRefreshFileBrowser();
        }
      };

      // 文件浏览器导航到首页
      const handleFileBrowserGoToHome = () => {
        refData.fileBrowserPath.value = "/mnt";
        updateFileBrowserCanNavigateUp();
        handleRefreshFileBrowser();
      };

      // 文件浏览器点击行
      const handleFileBrowserRowClick = (row) => {
        if (row.isDirectory) {
          const newPath = refData.fileBrowserPath.value === "/" 
            ? `/${row.name}` 
            : `${refData.fileBrowserPath.value}/${row.name}`;
          refData.fileBrowserPath.value = newPath;
          updateFileBrowserCanNavigateUp();
          handleRefreshFileBrowser();
        } else {
          // 点击文件时切换选择状态
          handleToggleFileSelection(row);
        }
      };

      // 切换文件选择状态
      const handleToggleFileSelection = (row) => {
        const filePath = refData.fileBrowserPath.value === "/" 
          ? `/${row.name}` 
          : `${refData.fileBrowserPath.value}/${row.name}`;
        const index = refData.selectedFiles.value.indexOf(filePath);
        if (index > -1) {
          refData.selectedFiles.value.splice(index, 1);
        } else {
          refData.selectedFiles.value.push(filePath);
        }
      };

      // 检查文件是否被选中
      const isFileSelected = (row) => {
        const filePath = refData.fileBrowserPath.value === "/" 
          ? `/${row.name}` 
          : `${refData.fileBrowserPath.value}/${row.name}`;
        return refData.selectedFiles.value.includes(filePath);
      };

      // 文件浏览器是否可以导航到上一级
      const fileBrowserCanNavigateUp = ref(false);
      const updateFileBrowserCanNavigateUp = () => {
        const path = refData.fileBrowserPath.value;
        fileBrowserCanNavigateUp.value = path && path !== "/mnt" && path !== "/";
      };

      // 添加文件到播放列表
      const handleAddFilesToPlaylist = async () => {
        if (refData.selectedFiles.value.length === 0) {
          ElMessage.warning("请先选择要添加的文件");
          return;
        }
        if (!refData.playlistStatus.value) {
          ElMessage.warning("请先创建并选择一个播放列表");
          return;
        }

        try {
          refData.playlistLoading.value = true;
          
          let deviceAddress = refData.playlistStatus.value.device_address;

          // 如果没有设备地址，尝试获取已连接的设备
          if (!deviceAddress && refData.connectedDeviceList.value.length > 0) {
            const connectedDevice = refData.connectedDeviceList.value.find((d) => d.connected);
            if (connectedDevice) {
              deviceAddress = connectedDevice.address;
            } else if (refData.connectedDeviceList.value.length > 0) {
              deviceAddress = refData.connectedDeviceList.value[0].address;
            }
          }

          await updateActivePlaylistData((playlistInfo) => {
            const list = Array.isArray(playlistInfo.playlist) ? [...playlistInfo.playlist] : [];
            for (const filePath of refData.selectedFiles.value) {
              if (!list.includes(filePath)) {
                list.push(filePath);
              }
            }
            playlistInfo.playlist = list;
            playlistInfo.total = list.length;
            playlistInfo.device_address = deviceAddress || playlistInfo.device_address;
            if (list.length === 0) {
              playlistInfo.current_index = 0;
            } else if (playlistInfo.current_index >= list.length) {
              playlistInfo.current_index = list.length - 1;
            }
            return playlistInfo;
          });

          ElMessage.success(`成功添加 ${refData.selectedFiles.value.length} 个文件到播放列表`);
          handleCloseFileBrowser();
        } catch (error) {
          console.error("添加文件到播放列表失败:", error);
          ElMessage.error("添加文件到播放列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      const refMethods = {
        handleUpdateDeviceList,
        handleOpenScanDialog,
        handleCloseScanDialog,
        handleOpenCronBuilder,
        handleCloseCronBuilder,
        updateCronExpression,
        handleApplyCronExpression,
        applyExample,
        handlePreviewGeneratedCron,
        handlePreviewCron,
        updateNextRunTime,
        formatSize,
        formatDurationMinutes,
        handleConnectDevice,
        handleDisconnectDevice,
        refreshConnectedList,
        // 播放列表相关
        refreshPlaylistStatus,
        handlePlayPlaylist,
        handlePlayNext,
        handleStopPlaylist,
        getCurrentPlaylistFile,
        // 播放列表管理
        handleMovePlaylistItemUp,
        handleMovePlaylistItemDown,
        handleDeletePlaylistItem,
        handleSelectPlaylist,
        handleCreatePlaylist,
        handleDeletePlaylistGroup,
        // 文件浏览相关
        handleOpenFileBrowser,
        handleCloseFileBrowser,
        handleRefreshFileBrowser,
        handleFileBrowserNavigateUp,
        handleFileBrowserGoToHome,
        handleFileBrowserRowClick,
        handleToggleFileSelection,
        isFileSelected,
        handleAddFilesToPlaylist,
        // Cron 相关
        handleToggleCronEnabled,
        handleDialogClose: () => {
          refData.dialogForm.value.visible = false;
          refData.dialogForm.value.value = 0;
        },
      };
      
      // 初始化文件浏览器导航
      updateFileBrowserCanNavigateUp();
      
      onMounted(async () => {
        await Promise.all([
          loadCronConfigFromRds(),
          loadPlaylistFromRds(),
          refreshConnectedList(),
        ]);
        updateNextRunTime();
      });
      
      // 监听 Cron 表达式变化，自动更新下次运行时间（在 onMounted 之后设置）
      watch(() => refData.cronExpression.value, () => {
        updateNextRunTime();
      });
      return {
        ...refData,
        fileBrowserCanNavigateUp,
        ...refMethods,
      };
    },
    template,
  };
  return component;
}
export default createComponent();
