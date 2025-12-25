/**
 * 批量模式管理器组件
 * 管理Batch列表和批量操作播放列表
 */
import { getRdsData, setRdsData } from "../../js/net_util.js";
import { logAndNoticeError } from "../../js/utils.js";
import { createFileDialog } from "./file_dialog.js";

const { ref, watch, computed, onMounted } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;

async function loadTemplate() {
    const response = await fetch(`./view/common/batch_manager-template.html?t=${Date.now()}`);
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
export async function createBatchManager(options = {}) {
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
            const batchList = ref([]);
            const selectedBatchId = ref(null);
            const selectedPlaylistId = ref(null);
            const selectedPreLists = ref([]); // 选中的前置文件列表索引 [0-6]
            const selectedFilesList = ref(false); // 是否选中正式文件列表
            const batchDeleteMode = ref(false); // 批量删除模式
            const selectedFileIndices = ref([]); // 选中的文件索引数组
            const fileBrowserDialogVisible = ref(false);
            const fileBrowserLoading = ref(false);
            const loading = ref(false);

            // RDS表名和ID
            const RDS_TABLE = 't_batch_list';
            const RDS_ID = '0';

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

            // 计算是否有选中的文件
            const hasSelectedFiles = computed(() => {
                return selectedFileIndices.value.length > 0;
            });

            // 计算是否全选
            const isAllFilesSelected = computed(() => {
                if (!selectedBatch.value || !selectedBatch.value.files || selectedBatch.value.files.length === 0) {
                    return false;
                }
                return selectedFileIndices.value.length === selectedBatch.value.files.length && selectedFileIndices.value.length > 0;
            });

            // 获取前置文件数量
            const getPreFilesCount = (weekdayIndex) => {
                const playlist = selectedPlaylist.value;
                if (!playlist || !playlist.pre_lists || !Array.isArray(playlist.pre_lists) || playlist.pre_lists.length !== 7) {
                    return 0;
                }
                const preList = playlist.pre_lists[weekdayIndex];
                return Array.isArray(preList) ? preList.length : 0;
            };

            // 获取前置文件列表中符合条件的文件数
            const getPreMatchedFileCount = (weekdayIndex) => {
                if (!selectedBatch.value || !selectedPlaylist.value) return 0;
                const batchFiles = selectedBatch.value.files || [];
                if (batchFiles.length === 0) return 0;

                const playlist = selectedPlaylist.value;
                if (!playlist || !playlist.pre_lists || !Array.isArray(playlist.pre_lists) || playlist.pre_lists.length !== 7) {
                    return 0;
                }

                const preList = playlist.pre_lists[weekdayIndex];
                if (!Array.isArray(preList)) return 0;

                const batchUriSet = new Set(batchFiles.map(f => f.uri || f));
                let matchedCount = 0;
                preList.forEach(file => {
                    const uri = file.uri || file;
                    if (batchUriSet.has(uri)) {
                        matchedCount++;
                    }
                });
                return matchedCount;
            };

            // 获取正式文件数量
            const getFilesListCount = () => {
                const playlist = selectedPlaylist.value;
                if (!playlist || !playlist.playlist || !Array.isArray(playlist.playlist)) {
                    return 0;
                }
                return playlist.playlist.length;
            };

            // 获取正式文件列表中符合条件的文件数
            const getFilesListMatchedCount = () => {
                if (!selectedBatch.value || !selectedPlaylist.value) return 0;
                const batchFiles = selectedBatch.value.files || [];
                if (batchFiles.length === 0) return 0;

                const playlist = selectedPlaylist.value;
                if (!playlist || !playlist.playlist || !Array.isArray(playlist.playlist)) {
                    return 0;
                }

                const batchUriSet = new Set(batchFiles.map(f => f.uri || f));
                let matchedCount = 0;
                playlist.playlist.forEach(file => {
                    const uri = file.uri || file;
                    if (batchUriSet.has(uri)) {
                        matchedCount++;
                    }
                });
                return matchedCount;
            };

            // 获取播放列表的总文件数（前置文件+正式文件）
            const getPlaylistTotalFileCount = (playlist) => {
                if (!playlist) return 0;
                let count = 0;
                // 前置文件（7个列表的总和）
                if (playlist.pre_lists && Array.isArray(playlist.pre_lists) && playlist.pre_lists.length === 7) {
                    playlist.pre_lists.forEach(preList => {
                        if (Array.isArray(preList)) {
                            count += preList.length;
                        }
                    });
                }
                // 正式文件
                if (playlist.playlist && Array.isArray(playlist.playlist)) {
                    count += playlist.playlist.length;
                }
                return count;
            };

            // 获取播放列表中命中当前Batch的文件数
            const getMatchedFileCount = (playlist) => {
                if (!selectedBatch.value || !playlist) return 0;
                const batchFiles = selectedBatch.value.files || [];
                if (batchFiles.length === 0) return 0;

                const batchUriSet = new Set(batchFiles.map(f => f.uri || f));
                let matchedCount = 0;

                // 检查前置文件
                if (playlist.pre_lists && Array.isArray(playlist.pre_lists) && playlist.pre_lists.length === 7) {
                    playlist.pre_lists.forEach(preList => {
                        if (Array.isArray(preList)) {
                            preList.forEach(file => {
                                const uri = file.uri || file;
                                if (batchUriSet.has(uri)) {
                                    matchedCount++;
                                }
                            });
                        }
                    });
                }

                // 检查正式文件
                if (playlist.playlist && Array.isArray(playlist.playlist)) {
                    playlist.playlist.forEach(file => {
                        const uri = file.uri || file;
                        if (batchUriSet.has(uri)) {
                            matchedCount++;
                        }
                    });
                }

                return matchedCount;
            };

            // 从RDS加载Batch列表
            const loadBatchList = async () => {
                try {
                    loading.value = true;
                    const data = await getRdsData(RDS_TABLE, RDS_ID);

                    // 检查数据是否存在且不为空字符串
                    if (data !== null && data !== undefined && typeof data === 'string' && data.trim() !== '') {
                        try {
                            const parsed = JSON.parse(data);
                            if (Array.isArray(parsed)) {
                                batchList.value = parsed;
                                // 默认选择第一个Batch
                                if (batchList.value.length > 0 && !selectedBatchId.value) {
                                    selectedBatchId.value = batchList.value[0].id;
                                }
                            } else {
                                batchList.value = [];
                            }
                        } catch (e) {
                            batchList.value = [];
                        }
                    } else if (Array.isArray(data)) {
                        // 如果后端直接返回数组（虽然不太可能）
                        batchList.value = data;
                        // 默认选择第一个Batch
                        if (batchList.value.length > 0 && !selectedBatchId.value) {
                            selectedBatchId.value = batchList.value[0].id;
                        }
                    } else {
                        batchList.value = [];
                    }
                } catch (error) {
                    batchList.value = [];
                } finally {
                    loading.value = false;
                }
            };

            // 保存Batch列表到RDS
            const saveBatchList = async () => {
                try {
                    const dataToSave = JSON.stringify(batchList.value);
                    await setRdsData(RDS_TABLE, RDS_ID, dataToSave);
                } catch (error) {
                    logAndNoticeError(error, '保存Batch列表失败');
                    throw error;
                }
            };

            // 创建Batch
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

            // 编辑Batch名称
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

            // 删除Batch
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

            // 切换批量删除模式
            const handleToggleBatchDeleteMode = () => {
                batchDeleteMode.value = !batchDeleteMode.value;
                if (!batchDeleteMode.value) {
                    // 退出批量删除模式时清空选中项
                    selectedFileIndices.value = [];
                }
            };

            // 选择Batch
            const handleSelectBatch = (batchId) => {
                selectedBatchId.value = batchId;
                // 切换Batch时清空选中的文件和退出批量删除模式
                selectedFileIndices.value = [];
                batchDeleteMode.value = false;
            };

            // 切换文件选中状态
            const handleToggleFileSelection = (index) => {
                const indices = selectedFileIndices.value;
                const pos = indices.indexOf(index);
                if (pos > -1) {
                    indices.splice(pos, 1);
                } else {
                    indices.push(index);
                }
            };

            // 全选/取消全选文件
            const handleToggleAllFiles = () => {
                if (!selectedBatch.value || !selectedBatch.value.files || selectedBatch.value.files.length === 0) {
                    return;
                }
                if (isAllFilesSelected.value) {
                    // 取消全选
                    selectedFileIndices.value = [];
                } else {
                    // 全选
                    selectedFileIndices.value = [];
                    selectedBatch.value.files.forEach((_, index) => {
                        selectedFileIndices.value.push(index);
                    });
                }
            };

            // 批量删除选中的文件
            const handleBatchDeleteFiles = async () => {
                if (!selectedBatch.value || selectedFileIndices.value.length === 0) {
                    return;
                }
                try {
                    const selectedCount = selectedFileIndices.value.length;
                    await ElMessageBox.confirm(
                        `确定要删除选中的 ${selectedCount} 个文件吗？`,
                        '确认批量删除',
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
                    // 清空选中项并退出批量删除模式
                    selectedFileIndices.value = [];
                    batchDeleteMode.value = false;
                    await saveBatchList();
                    ElMessage.success(`已删除 ${selectedCount} 个文件`);
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '批量删除失败');
                    }
                }
            };

            // 选择播放列表
            const handleSelectPlaylist = (playlistId) => {
                // 如果点击的是已选中的播放列表，则取消选中
                if (selectedPlaylistId.value === playlistId) {
                    selectedPlaylistId.value = null;
                } else {
                    selectedPlaylistId.value = playlistId;
                }
                // 重置选中状态
                selectedPreLists.value = [];
                selectedFilesList.value = false;
            };

            // 切换前置文件列表选中状态
            const handleTogglePreList = (weekdayIndex) => {
                const index = selectedPreLists.value.indexOf(weekdayIndex);
                if (index > -1) {
                    selectedPreLists.value.splice(index, 1);
                } else {
                    selectedPreLists.value.push(weekdayIndex);
                }
            };

            // 切换正式文件列表选中状态
            const handleToggleFilesList = (checked) => {
                // 如果传入了参数，使用参数值；否则切换状态
                if (checked !== undefined) {
                    selectedFilesList.value = checked;
                } else {
                    selectedFilesList.value = !selectedFilesList.value;
                }
            };

            // 打开文件浏览器
            const handleOpenFileBrowser = () => {
                if (!selectedBatch.value) {
                    ElMessage.warning('请先选择一个Batch');
                    return;
                }
                fileBrowserDialogVisible.value = true;
            };

            // 文件浏览器确认
            const handleFileBrowserConfirm = async (filePaths) => {
                if (!selectedBatch.value || filePaths.length === 0) return;
                try {
                    fileBrowserLoading.value = true;
                    const batch = selectedBatch.value;
                    const existingUris = new Set();
                    batch.files.forEach(file => {
                        const uri = file.uri || file;
                        existingUris.add(uri);
                    });

                    // 添加新文件，去重
                    filePaths.forEach(filePath => {
                        if (!existingUris.has(filePath)) {
                            batch.files.push({ uri: filePath });
                            existingUris.add(filePath);
                        }
                    });

                    await saveBatchList();
                    ElMessage.success(`成功添加 ${filePaths.length} 个文件`);
                    fileBrowserDialogVisible.value = false;
                } catch (error) {
                    logAndNoticeError(error, '添加文件失败');
                } finally {
                    fileBrowserLoading.value = false;
                }
            };

            // 关闭文件浏览器
            const handleCloseFileBrowser = () => {
                fileBrowserDialogVisible.value = false;
            };

            // 从Batch中删除文件
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

            // 清空Batch中的所有文件
            const handleClearBatchFiles = async () => {
                if (!selectedBatch.value || !selectedBatch.value.files || selectedBatch.value.files.length === 0) {
                    return;
                }
                try {
                    await ElMessageBox.confirm(
                        `确定要清空Batch "${selectedBatch.value.name}" 中的所有文件吗？`,
                        '确认清空',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );
                    selectedBatch.value.files = [];
                    await saveBatchList();
                    ElMessage.success('文件已清空');
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '清空文件失败');
                    }
                }
            };

            // 添加文件到播放列表
            const handleAddFilesToPlaylist = async () => {
                if (!selectedBatch.value || !selectedPlaylistId.value || selectedBatch.value.files.length === 0 || !hasSelectedLists.value) {
                    ElMessage.warning('请选择Batch、播放列表和目标列表');
                    return;
                }

                try {
                    await ElMessageBox.confirm(
                        `确定要将Batch "${selectedBatch.value.name}" 中的所有文件添加到选中的列表吗？`,
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
                            files: selectedBatch.value.files.map(f => f.uri || f),
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

            // 从播放列表删除文件
            const handleRemoveFilesFromPlaylist = async () => {
                if (!selectedBatch.value || !selectedPlaylistId.value || selectedBatch.value.files.length === 0 || !hasSelectedLists.value) {
                    ElMessage.warning('请选择Batch、播放列表和目标列表');
                    return;
                }

                try {
                    await ElMessageBox.confirm(
                        `确定要从选中的列表中删除Batch "${selectedBatch.value.name}" 中的所有文件吗？`,
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
                            files: selectedBatch.value.files.map(f => f.uri || f),
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

            // 关闭浮层
            const handleClose = () => {
                emit('update:visible', false);
            };

            // 监听播放列表集合变化，默认选择第一个
            watch(() => props.playlistCollection, (newCollection) => {
                if (newCollection && newCollection.length > 0 && !selectedPlaylistId.value) {
                    selectedPlaylistId.value = newCollection[0].id;
                }
            }, { immediate: true });

            // 监听visible变化，加载数据
            watch(() => props.visible, (newVal) => {
                if (newVal) {
                    // 先重置其他选择状态，但保留selectedBatchId（让loadBatchList自动选择第一个）
                    selectedPreLists.value = [];
                    selectedFilesList.value = false;
                    selectedFileIndices.value = [];
                    batchDeleteMode.value = false;
                    // 默认选择第一个播放列表
                    if (props.playlistCollection && props.playlistCollection.length > 0) {
                        selectedPlaylistId.value = props.playlistCollection[0].id;
                    } else {
                        selectedPlaylistId.value = null;
                    }
                    // 加载数据（加载完成后会自动选择第一个Batch）
                    loadBatchList();
                } else {
                    // 关闭时清空所有选择
                    selectedBatchId.value = null;
                    selectedPlaylistId.value = null;
                    selectedPreLists.value = [];
                    selectedFilesList.value = false;
                    selectedFileIndices.value = [];
                    batchDeleteMode.value = false;
                }
            }, { immediate: true });

            // 组件挂载时也加载数据（如果visible为true）
            onMounted(() => {
                // 无论visible是否为true，都尝试加载一次（因为watch可能没有触发）
                loadBatchList();
            });

            return {
                batchList,
                selectedBatchId,
                selectedPlaylistId,
                selectedPreLists,
                selectedFilesList,
                batchDeleteMode,
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
                loadBatchList, // 暴露出来以便调试
                handleCreateBatch,
                handleEditBatch,
                handleDeleteBatch,
                handleSelectBatch,
                handleSelectPlaylist,
                handleTogglePreList,
                handleToggleFilesList,
                handleToggleBatchDeleteMode,
                handleOpenFileBrowser,
                handleFileBrowserConfirm,
                handleCloseFileBrowser,
                handleRemoveFileFromBatch,
                handleClearBatchFiles,
                handleToggleFileSelection,
                handleToggleAllFiles,
                handleBatchDeleteFiles,
                handleAddFilesToPlaylist,
                handleRemoveFilesFromPlaylist,
                handleClose,
            };
        },
        template,
    };
}

