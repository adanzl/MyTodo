/**
 * 批量模式管理器组件
 * 管理Batch列表和批量操作播放列表
 */
import { getRdsData, setRdsData } from "../../js/net_util.js";
import { logAndNoticeError } from "../../js/utils.js";
import { createFileDialog } from "./file_dialog.js";

const { ref, watch, computed, onMounted } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;

// 常量
const RDS_TABLE = 't_batch_list';
const RDS_ID = '0';
const PRE_LISTS_COUNT = 7; // 前置文件列表数量

async function loadTemplate() {
    const response = await fetch(`./view/sub_view/batch_drawer-template.html?t=${Date.now()}`);
    return await response.text();
}

/**
 * 创建批量模式管理器组件
 * @param {Object} options - 配置选项
 * @param {Function} options.onAddFiles - 添加文件到播放列表的回调
 * @param {Function} options.onRemoveFiles - 从播放列表删除文件的回调
 * @param {Array} options.playlistCollection - 播放列表集合
 * @returns {Object} Vue组件
 */
export async function createBatchDrawer(options = {}) {
    const {
        onAddFiles = null,
        onRemoveFiles = null,
    } = options;

    const template = await loadTemplate();
    const FileDialog = await createFileDialog();

    return {
        components: {
            FileDialog,
        },
        props: {
            visible: {
                type: Boolean,
                default: false,
            },
            playlistCollection: {
                type: Array,
                default: () => [],
            },
        },
        emits: ['update:visible', 'refresh'],
        setup(props, { emit }) {
            // 状态
            const batchList = ref([]);
            const selectedBatchId = ref(null);
            const selectedPlaylistId = ref(null);
            const selectedPreLists = ref([]); // 选中的前置文件列表索引 [0-6]
            const selectedFilesList = ref(false); // 是否选中正式文件列表
            const selectedFileIndices = ref([]); // 选中的文件索引数组
            const fileBrowserDialogVisible = ref(false);
            const fileBrowserLoading = ref(false);
            const loading = ref(false);

            // 计算属性
            const selectedBatch = computed(() => {
                return batchList.value.find(b => b.id === selectedBatchId.value) || null;
            });

            const selectedPlaylist = computed(() => {
                return props.playlistCollection.find(p => p.id === selectedPlaylistId.value) || null;
            });

            const hasSelectedLists = computed(() => {
                return selectedPreLists.value.length > 0 || selectedFilesList.value;
            });

            const hasSelectedFiles = computed(() => {
                return selectedFileIndices.value.length > 0;
            });

            const isAllFilesSelected = computed(() => {
                if (!selectedBatch.value?.files?.length) return false;
                return selectedFileIndices.value.length === selectedBatch.value.files.length && selectedFileIndices.value.length > 0;
            });

            // ========== 辅助函数 ==========

            /**
             * 获取文件的URI
             */
            const getFileUri = (file) => file?.uri || file;

            /**
             * 获取选中的文件对象数组
             */
            const getSelectedFiles = () => {
                if (!selectedBatch.value?.files) return [];
                return selectedFileIndices.value
                    .map(index => selectedBatch.value.files[index])
                    .filter(f => f !== null);
            };

            /**
             * 获取选中文件的URI集合
             */
            const getSelectedFileUris = () => {
                return new Set(getSelectedFiles().map(getFileUri));
            };

            /**
             * 验证播放列表的前置文件列表结构
             */
            const isValidPreLists = (playlist) => {
                return playlist?.pre_lists &&
                    Array.isArray(playlist.pre_lists) &&
                    playlist.pre_lists.length === PRE_LISTS_COUNT;
            };

            /**
             * 验证播放列表的正式文件列表结构
             */
            const isValidFilesList = (playlist) => {
                return playlist?.playlist && Array.isArray(playlist.playlist);
            };

            /**
             * 计算列表中匹配的文件数量
             */
            const countMatchedFiles = (fileList, uriSet) => {
                if (!Array.isArray(fileList)) return 0;
                let count = 0;
                fileList.forEach(file => {
                    if (uriSet.has(getFileUri(file))) {
                        count++;
                    }
                });
                return count;
            };

            /**
             * 选择第一个Batch并全选文件
             */
            const selectFirstBatchAndFiles = () => {
                if (batchList.value.length === 0 || selectedBatchId.value) return;

                const firstBatch = batchList.value[0];
                selectedBatchId.value = firstBatch.id;

                if (firstBatch?.files?.length > 0) {
                    selectedFileIndices.value = firstBatch.files.map((_, index) => index);
                }
            };

            /**
             * 切换数组中的元素（存在则移除，不存在则添加）
             */
            const toggleArrayItem = (array, item) => {
                const index = array.indexOf(item);
                if (index > -1) {
                    array.splice(index, 1);
                } else {
                    array.push(item);
                }
            };

            // ========== 获取函数 ==========

            /**
             * 获取前置文件数量
             */
            const getPreFilesCount = (weekdayIndex) => {
                const playlist = selectedPlaylist.value;
                if (!isValidPreLists(playlist)) return 0;
                const preList = playlist.pre_lists[weekdayIndex];
                return Array.isArray(preList) ? preList.length : 0;
            };

            /**
             * 获取前置文件列表中符合条件的文件数（只统计选中的文件）
             */
            const getPreMatchedFileCount = (weekdayIndex) => {
                if (!selectedBatch.value || !selectedPlaylist.value) return 0;
                const uriSet = getSelectedFileUris();
                if (uriSet.size === 0) return 0;

                const playlist = selectedPlaylist.value;
                if (!isValidPreLists(playlist)) return 0;

                const preList = playlist.pre_lists[weekdayIndex];
                return countMatchedFiles(preList, uriSet);
            };

            /**
             * 获取正式文件数量
             */
            const getFilesListCount = () => {
                const playlist = selectedPlaylist.value;
                if (!isValidFilesList(playlist)) return 0;
                return playlist.playlist.length;
            };

            /**
             * 获取正式文件列表中符合条件的文件数（只统计选中的文件）
             */
            const getFilesListMatchedCount = () => {
                if (!selectedBatch.value || !selectedPlaylist.value) return 0;
                const uriSet = getSelectedFileUris();
                if (uriSet.size === 0) return 0;

                const playlist = selectedPlaylist.value;
                if (!isValidFilesList(playlist)) return 0;

                return countMatchedFiles(playlist.playlist, uriSet);
            };

            /**
             * 获取播放列表的总文件数（前置文件+正式文件）
             */
            const getPlaylistTotalFileCount = (playlist) => {
                if (!playlist) return 0;
                let count = 0;

                // 前置文件（7个列表的总和）
                if (isValidPreLists(playlist)) {
                    playlist.pre_lists.forEach(preList => {
                        if (Array.isArray(preList)) {
                            count += preList.length;
                        }
                    });
                }

                // 正式文件
                if (isValidFilesList(playlist)) {
                    count += playlist.playlist.length;
                }

                return count;
            };

            /**
             * 获取播放列表中命中当前Batch选中文件的文件数
             */
            const getMatchedFileCount = (playlist) => {
                if (!selectedBatch.value || !playlist) return 0;
                const uriSet = getSelectedFileUris();
                if (uriSet.size === 0) return 0;

                let matchedCount = 0;

                // 检查前置文件
                if (isValidPreLists(playlist)) {
                    playlist.pre_lists.forEach(preList => {
                        matchedCount += countMatchedFiles(preList, uriSet);
                    });
                }

                // 检查正式文件
                if (isValidFilesList(playlist)) {
                    matchedCount += countMatchedFiles(playlist.playlist, uriSet);
                }

                return matchedCount;
            };

            // ========== 数据操作 ==========

            /**
             * 从RDS加载Batch列表
             */
            const loadBatchList = async () => {
                try {
                    loading.value = true;
                    const data = await getRdsData(RDS_TABLE, RDS_ID);

                    let parsedList = [];

                    // 解析数据
                    if (data !== null && data !== undefined) {
                        if (typeof data === 'string' && data.trim() !== '') {
                            try {
                                const parsed = JSON.parse(data);
                                parsedList = Array.isArray(parsed) ? parsed : [];
                            } catch (e) {
                                parsedList = [];
                            }
                        } else if (Array.isArray(data)) {
                            parsedList = data;
                        }
                    }

                    batchList.value = parsedList;
                    selectFirstBatchAndFiles();
                } catch (error) {
                    batchList.value = [];
                    logAndNoticeError(error, '加载Batch列表失败');
                } finally {
                    loading.value = false;
                }
            };

            /**
             * 保存Batch列表到RDS
             */
            const saveBatchList = async () => {
                try {
                    const dataToSave = JSON.stringify(batchList.value);
                    await setRdsData(RDS_TABLE, RDS_ID, dataToSave);
                } catch (error) {
                    logAndNoticeError(error, '保存Batch列表失败');
                    throw error;
                }
            };

            // ========== Batch操作 ==========

            /**
             * 创建Batch
             */
            const handleCreateBatch = async () => {
                try {
                    const { value } = await ElMessageBox.prompt(
                        '请输入Batch名称',
                        '创建Batch',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            inputPlaceholder: 'Batch名称',
                            inputValidator: (val) => (!!val && val.trim().length > 0) || '名称不能为空',
                        }
                    );
                    const name = value.trim();
                    const newBatch = {
                        id: Date.now().toString(),
                        name,
                        files: [],
                        createTime: new Date().toISOString(),
                    };
                    batchList.value.push(newBatch);
                    await saveBatchList();
                    ElMessage.success('Batch创建成功');
                    selectedBatchId.value = newBatch.id;
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '创建Batch失败');
                    }
                }
            };

            /**
             * 编辑Batch名称
             */
            const handleEditBatch = async (batchId) => {
                const batch = batchList.value.find(b => b.id === batchId);
                if (!batch) return;
                try {
                    const { value } = await ElMessageBox.prompt(
                        '请输入Batch名称',
                        '编辑Batch',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            inputValue: batch.name,
                            inputPlaceholder: 'Batch名称',
                            inputValidator: (val) => (!!val && val.trim().length > 0) || '名称不能为空',
                        }
                    );
                    batch.name = value.trim();
                    await saveBatchList();
                    ElMessage.success('Batch名称已更新');
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '编辑Batch失败');
                    }
                }
            };

            /**
             * 删除Batch
             */
            const handleDeleteBatch = async (batchId) => {
                const batch = batchList.value.find(b => b.id === batchId);
                if (!batch) return;
                try {
                    await ElMessageBox.confirm(
                        `确定要删除Batch "${batch.name}" 吗？`,
                        '确认删除',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );
                    const index = batchList.value.findIndex(b => b.id === batchId);
                    if (index > -1) {
                        batchList.value.splice(index, 1);
                        await saveBatchList();
                        if (selectedBatchId.value === batchId) {
                            selectedBatchId.value = null;
                        }
                        ElMessage.success('Batch已删除');
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '删除Batch失败');
                    }
                }
            };

            /**
             * 选择Batch
             */
            const handleSelectBatch = (batchId) => {
                selectedBatchId.value = batchId;
                const batch = batchList.value.find(b => b.id === batchId);
                if (batch?.files?.length > 0) {
                    selectedFileIndices.value = batch.files.map((_, index) => index);
                } else {
                    selectedFileIndices.value = [];
                }
            };

            // ========== 文件操作 ==========

            /**
             * 切换文件选中状态
             */
            const handleToggleFileSelection = (index) => {
                toggleArrayItem(selectedFileIndices.value, index);
            };

            /**
             * 删除所选文件
             */
            const handleDeleteSelectedFiles = async () => {
                if (!selectedBatch.value || selectedFileIndices.value.length === 0) {
                    return;
                }
                try {
                    const selectedCount = selectedFileIndices.value.length;
                    await ElMessageBox.confirm(
                        `确定要删除选中的 ${selectedCount} 个文件吗？`,
                        '确认删除',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );
                    // 去重并排序（从大到小，避免删除时索引变化）
                    const indicesToDelete = [...new Set(selectedFileIndices.value)].sort((a, b) => b - a);
                    // 从后往前删除，避免索引变化
                    indicesToDelete.forEach(index => {
                        if (index >= 0 && index < selectedBatch.value.files.length) {
                            selectedBatch.value.files.splice(index, 1);
                        }
                    });
                    // 删除后重新设置选中项（保留剩余文件的选中状态）
                    if (selectedBatch.value.files.length > 0) {
                        selectedFileIndices.value = selectedBatch.value.files.map((_, index) => index);
                    } else {
                        selectedFileIndices.value = [];
                    }
                    await saveBatchList();
                    ElMessage.success(`已删除 ${selectedCount} 个文件`);
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '删除失败');
                    }
                }
            };

            /**
             * 打开文件浏览器
             */
            const handleOpenFileBrowser = () => {
                if (!selectedBatch.value) {
                    ElMessage.warning('请先选择一个Batch');
                    return;
                }
                fileBrowserDialogVisible.value = true;
            };

            /**
             * 文件浏览器确认
             */
            const handleFileBrowserConfirm = async (filePaths) => {
                if (!selectedBatch.value || filePaths.length === 0) return;
                try {
                    fileBrowserLoading.value = true;
                    const batch = selectedBatch.value;
                    const existingUris = new Set(batch.files.map(getFileUri));

                    // 添加新文件，去重
                    const newFiles = filePaths
                        .filter(filePath => !existingUris.has(filePath))
                        .map(filePath => ({ uri: filePath }));

                    batch.files.push(...newFiles);

                    await saveBatchList();
                    // 添加文件后，默认全选所有文件
                    if (batch.files.length > 0) {
                        selectedFileIndices.value = batch.files.map((_, index) => index);
                    }
                    ElMessage.success(`成功添加 ${newFiles.length} 个文件`);
                    fileBrowserDialogVisible.value = false;
                } catch (error) {
                    logAndNoticeError(error, '添加文件失败');
                } finally {
                    fileBrowserLoading.value = false;
                }
            };

            /**
             * 关闭文件浏览器
             */
            const handleCloseFileBrowser = () => {
                fileBrowserDialogVisible.value = false;
            };

            /**
             * 从Batch中删除文件
             */
            const handleRemoveFileFromBatch = async (index) => {
                if (!selectedBatch.value) return;
                try {
                    await ElMessageBox.confirm(
                        '确定要删除该文件吗？',
                        '确认删除',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );
                    selectedBatch.value.files.splice(index, 1);
                    await saveBatchList();
                    ElMessage.success('文件已删除');
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '删除文件失败');
                    }
                }
            };

            // ========== 播放列表操作 ==========

            /**
             * 选择播放列表
             */
            const handleSelectPlaylist = (playlistId) => {
                // 如果点击的是已选中的播放列表，则取消选中
                selectedPlaylistId.value = selectedPlaylistId.value === playlistId ? null : playlistId;
                // 重置选中状态
                selectedPreLists.value = [];
                selectedFilesList.value = false;
            };

            /**
             * 切换前置文件列表选中状态
             */
            const handleTogglePreList = (weekdayIndex) => {
                toggleArrayItem(selectedPreLists.value, weekdayIndex);
            };

            /**
             * 切换正式文件列表选中状态
             */
            const handleToggleFilesList = (checked) => {
                selectedFilesList.value = checked !== undefined ? checked : !selectedFilesList.value;
            };

            /**
             * 验证操作条件
             */
            const validateOperation = () => {
                if (!selectedBatch.value || !selectedPlaylistId.value || selectedFileIndices.value.length === 0 || !hasSelectedLists.value) {
                    ElMessage.warning('请选择Batch、播放列表和目标列表，并至少选中一个文件');
                    return false;
                }
                return true;
            };

            /**
             * 添加文件到播放列表（只添加选中的文件）
             */
            const handleAddFilesToPlaylist = async () => {
                if (!validateOperation()) return;

                try {
                    const fileUris = getSelectedFiles().map(getFileUri);

                    await ElMessageBox.confirm(
                        `确定要将选中的 ${fileUris.length} 个文件添加到选中的列表吗？`,
                        '确认添加',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );

                    if (onAddFiles) {
                        await onAddFiles({
                            playlistId: selectedPlaylistId.value,
                            files: fileUris,
                            preLists: selectedPreLists.value,
                            filesList: selectedFilesList.value,
                        });
                        ElMessage.success('文件已添加到播放列表');
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '添加文件失败');
                    }
                }
            };

            /**
             * 从播放列表删除文件（只删除选中的文件）
             */
            const handleRemoveFilesFromPlaylist = async () => {
                if (!validateOperation()) return;

                try {
                    const fileUris = getSelectedFiles().map(getFileUri);

                    await ElMessageBox.confirm(
                        `确定要从选中的列表中删除选中的 ${fileUris.length} 个文件吗？`,
                        '确认删除',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );

                    if (onRemoveFiles) {
                        await onRemoveFiles({
                            playlistId: selectedPlaylistId.value,
                            files: fileUris,
                            preLists: selectedPreLists.value,
                            filesList: selectedFilesList.value,
                        });
                        ElMessage.success('文件已从播放列表删除');
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '删除文件失败');
                    }
                }
            };

            /**
             * 关闭浮层
             */
            const handleClose = () => {
                emit('update:visible', false);
            };

            /**
             * 重置选择状态
             */
            const resetSelection = () => {
                selectedPreLists.value = [];
                selectedFilesList.value = false;
                selectedFileIndices.value = [];
            };

            /**
             * 清空所有选择
             */
            const clearAllSelection = () => {
                selectedBatchId.value = null;
                selectedPlaylistId.value = null;
                resetSelection();
            };

            /**
             * 初始化播放列表选择
             */
            const initPlaylistSelection = () => {
                if (props.playlistCollection?.length > 0) {
                    selectedPlaylistId.value = props.playlistCollection[0].id;
                } else {
                    selectedPlaylistId.value = null;
                }
            };

            // ========== 监听器 ==========

            // 监听播放列表集合变化，默认选择第一个
            watch(() => props.playlistCollection, (newCollection) => {
                if (newCollection?.length > 0 && !selectedPlaylistId.value) {
                    selectedPlaylistId.value = newCollection[0].id;
                }
            }, { immediate: true });

            // 监听visible变化，加载数据
            watch(() => props.visible, (newVal) => {
                if (newVal) {
                    resetSelection();
                    initPlaylistSelection();
                    loadBatchList();
                } else {
                    clearAllSelection();
                }
            }, { immediate: true });

            // 组件挂载时也加载数据（如果visible为true）
            onMounted(() => {
                loadBatchList();
            });

            return {
                batchList,
                selectedBatchId,
                selectedPlaylistId,
                selectedPreLists,
                selectedFilesList,
                selectedFileIndices,
                fileBrowserDialogVisible,
                fileBrowserLoading,
                selectedBatch,
                selectedPlaylist,
                hasSelectedLists,
                hasSelectedFiles,
                isAllFilesSelected,
                getPreFilesCount,
                getPreMatchedFileCount,
                getFilesListCount,
                getFilesListMatchedCount,
                getPlaylistTotalFileCount,
                getMatchedFileCount,
                loadBatchList,
                handleCreateBatch,
                handleEditBatch,
                handleDeleteBatch,
                handleSelectBatch,
                handleSelectPlaylist,
                handleTogglePreList,
                handleToggleFilesList,
                handleOpenFileBrowser,
                handleFileBrowserConfirm,
                handleCloseFileBrowser,
                handleRemoveFileFromBatch,
                handleToggleFileSelection,
                handleDeleteSelectedFiles,
                handleAddFilesToPlaylist,
                handleRemoveFilesFromPlaylist,
                handleClose,
            };
        },
        template,
    };
}
