/**
 * 应用到列表选择器组件
 * 用于选择播放列表和子列表，支持复制或删除文件
 */
import { logAndNoticeError } from "../../js/utils.js";

const { ref, computed, watch, onMounted } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;

async function loadTemplate() {
    const response = await fetch(`./view/sub_view/playlist_select_dialog-template.html?t=${Date.now()}`);
    return await response.text();
}

/**
 * 创建应用到列表选择器组件
 * @param {Object} options - 配置选项
 * @param {Function} options.onCopy - 复制文件到列表的回调
 * @param {Function} options.onRemove - 从列表删除文件的回调
 * @param {Array} options.playlistCollection - 播放列表集合
 * @param {Array} options.selectedFiles - 选中的文件列表
 * @returns {Object} Vue组件
 */
export async function createPlaylistSelector(options = {}) {
    const {
        onCopy = null,
        onRemove = null,
    } = options;

    const template = await loadTemplate();

    return {
        props: {
            visible: {
                type: Boolean,
                default: false,
            },
            playlistCollection: {
                type: Array,
                default: () => [],
            },
            selectedFiles: {
                type: Array,
                default: () => [],
            },
        },
        emits: ['update:visible'],
        setup(props, { emit }) {
            const selectedPlaylistId = ref(null);
            const selectedPreLists = ref([]); // 选中的前置文件列表索引 [0-6]
            const selectedFilesList = ref(false); // 是否选中正式文件列表

            // 计算属性
            const selectedPlaylist = computed(() => {
                return props.playlistCollection.find(p => p.id === selectedPlaylistId.value) || null;
            });

            const hasSelectedLists = computed(() => {
                return selectedPreLists.value.length > 0 || selectedFilesList.value;
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

            // 获取正式文件数量
            const getFilesListCount = () => {
                const playlist = selectedPlaylist.value;
                if (!playlist || !playlist.playlist) {
                    return 0;
                }
                return Array.isArray(playlist.playlist) ? playlist.playlist.length : 0;
            };

            // 获取播放列表总文件数
            const getPlaylistTotalFileCount = (playlist) => {
                if (!playlist) return 0;
                const preCount = playlist.pre_lists && Array.isArray(playlist.pre_lists) && playlist.pre_lists.length === 7
                    ? playlist.pre_lists.reduce((sum, list) => sum + (Array.isArray(list) ? list.length : 0), 0)
                    : 0;
                const filesCount = Array.isArray(playlist.playlist) ? playlist.playlist.length : 0;
                return preCount + filesCount;
            };

            // 获取选中的文件URI集合
            const getSelectedFileUris = () => {
                if (!props.selectedFiles || props.selectedFiles.length === 0) {
                    return new Set();
                }
                return new Set(props.selectedFiles.map(f => {
                    if (typeof f === 'string') return f;
                    return f.uri || f;
                }));
            };

            // 获取播放列表中符合条件的文件数（选中的文件在该播放列表中存在的数量）
            const getMatchedFileCountInPlaylist = (playlist) => {
                if (!playlist || !props.selectedFiles || props.selectedFiles.length === 0) {
                    return 0;
                }
                const selectedFileUris = getSelectedFileUris();
                let matchedCount = 0;

                // 检查前置文件列表
                if (playlist.pre_lists && Array.isArray(playlist.pre_lists) && playlist.pre_lists.length === 7) {
                    playlist.pre_lists.forEach(preList => {
                        if (Array.isArray(preList)) {
                            preList.forEach(file => {
                                const fileUri = file.uri || file;
                                if (selectedFileUris.has(fileUri)) {
                                    matchedCount++;
                                }
                            });
                        }
                    });
                }

                // 检查正式文件列表
                if (Array.isArray(playlist.playlist)) {
                    playlist.playlist.forEach(file => {
                        const fileUri = file.uri || file;
                        if (selectedFileUris.has(fileUri)) {
                            matchedCount++;
                        }
                    });
                }

                return matchedCount;
            };

            // 获取前置文件列表中符合条件的文件数
            const getMatchedFileCountInPreList = (weekdayIndex) => {
                const playlist = selectedPlaylist.value;
                if (!playlist || !props.selectedFiles || props.selectedFiles.length === 0) {
                    return 0;
                }
                if (!playlist.pre_lists || !Array.isArray(playlist.pre_lists) || playlist.pre_lists.length !== 7) {
                    return 0;
                }
                const preList = playlist.pre_lists[weekdayIndex];
                if (!Array.isArray(preList)) {
                    return 0;
                }
                const selectedFileUris = getSelectedFileUris();
                let matchedCount = 0;
                preList.forEach(file => {
                    const fileUri = file.uri || file;
                    if (selectedFileUris.has(fileUri)) {
                        matchedCount++;
                    }
                });
                return matchedCount;
            };

            // 获取正式文件列表中符合条件的文件数
            const getMatchedFileCountInFilesList = () => {
                const playlist = selectedPlaylist.value;
                if (!playlist || !props.selectedFiles || props.selectedFiles.length === 0) {
                    return 0;
                }
                if (!Array.isArray(playlist.playlist)) {
                    return 0;
                }
                const selectedFileUris = getSelectedFileUris();
                let matchedCount = 0;
                playlist.playlist.forEach(file => {
                    const fileUri = file.uri || file;
                    if (selectedFileUris.has(fileUri)) {
                        matchedCount++;
                    }
                });
                return matchedCount;
            };

            // 选择播放列表
            const handleSelectPlaylist = (playlistId) => {
                selectedPlaylistId.value = playlistId;
                // 重置选择
                selectedPreLists.value = [];
                selectedFilesList.value = false;
            };

            // 切换前置文件列表选择
            const handleTogglePreList = (index) => {
                const pos = selectedPreLists.value.indexOf(index);
                if (pos > -1) {
                    selectedPreLists.value.splice(pos, 1);
                } else {
                    selectedPreLists.value.push(index);
                }
            };

            // 切换正式文件列表选择
            const handleToggleFilesList = () => {
                selectedFilesList.value = !selectedFilesList.value;
            };

            // 复制文件到列表
            const handleCopy = async () => {
                if (!selectedPlaylist.value || !props.selectedFiles || props.selectedFiles.length === 0 || !hasSelectedLists.value) {
                    ElMessage.warning('请选择播放列表和目标列表，并至少选中一个文件');
                    return;
                }

                try {
                    const fileUris = props.selectedFiles.map(f => {
                        if (typeof f === 'string') return f;
                        return f.uri || f;
                    });

                    const preListsCount = selectedPreLists.value.length;
                    const filesListSelected = selectedFilesList.value;
                    let targetDesc = '';
                    if (preListsCount > 0 && filesListSelected) {
                        targetDesc = `${preListsCount}个前置文件列表和正式文件列表`;
                    } else if (preListsCount > 0) {
                        const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
                        const selectedDays = selectedPreLists.value.map(i => dayNames[i]).join('、');
                        targetDesc = `前置文件列表（${selectedDays}）`;
                    } else if (filesListSelected) {
                        targetDesc = '正式文件列表';
                    }

                    await ElMessageBox.confirm(
                        `确定要将选中的 ${fileUris.length} 个文件复制到播放列表"${selectedPlaylist.value.name}"的${targetDesc}吗？`,
                        '确认复制',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );

                    if (onCopy) {
                        await onCopy({
                            playlistId: selectedPlaylistId.value,
                            files: fileUris,
                            preLists: selectedPreLists.value,
                            filesList: selectedFilesList.value,
                        });
                        ElMessage.success('文件已复制到播放列表');
                        handleClose();
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '复制文件失败');
                    }
                }
            };

            // 从列表删除文件
            const handleRemove = async () => {
                if (!selectedPlaylist.value || !props.selectedFiles || props.selectedFiles.length === 0 || !hasSelectedLists.value) {
                    ElMessage.warning('请选择播放列表和目标列表，并至少选中一个文件');
                    return;
                }

                try {
                    const fileUris = props.selectedFiles.map(f => {
                        if (typeof f === 'string') return f;
                        return f.uri || f;
                    });

                    const preListsCount = selectedPreLists.value.length;
                    const filesListSelected = selectedFilesList.value;
                    let targetDesc = '';
                    if (preListsCount > 0 && filesListSelected) {
                        targetDesc = `${preListsCount}个前置文件列表和正式文件列表`;
                    } else if (preListsCount > 0) {
                        const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
                        const selectedDays = selectedPreLists.value.map(i => dayNames[i]).join('、');
                        targetDesc = `前置文件列表（${selectedDays}）`;
                    } else if (filesListSelected) {
                        targetDesc = '正式文件列表';
                    }

                    await ElMessageBox.confirm(
                        `确定要从播放列表"${selectedPlaylist.value.name}"的${targetDesc}中删除选中的 ${fileUris.length} 个文件吗？`,
                        '确认删除',
                        {
                            confirmButtonText: '确定',
                            cancelButtonText: '取消',
                            type: 'warning',
                        }
                    );

                    if (onRemove) {
                        await onRemove({
                            playlistId: selectedPlaylistId.value,
                            files: fileUris,
                            preLists: selectedPreLists.value,
                            filesList: selectedFilesList.value,
                        });
                        ElMessage.success('文件已从播放列表删除');
                        handleClose();
                    }
                } catch (error) {
                    if (error !== 'cancel') {
                        logAndNoticeError(error, '删除文件失败');
                    }
                }
            };

            // 关闭对话框
            const handleClose = () => {
                emit('update:visible', false);
                // 重置选择
                selectedPlaylistId.value = null;
                selectedPreLists.value = [];
                selectedFilesList.value = false;
            };

            // 自动选择第一个播放列表
            const autoSelectFirstPlaylist = () => {
                if (props.playlistCollection && props.playlistCollection.length > 0 && !selectedPlaylistId.value) {
                    selectedPlaylistId.value = props.playlistCollection[0].id;
                }
            };

            // 监听播放列表集合变化，自动选择第一个
            watch(() => props.playlistCollection, (newCollection) => {
                if (newCollection && newCollection.length > 0 && !selectedPlaylistId.value) {
                    selectedPlaylistId.value = newCollection[0].id;
                }
            }, { immediate: true });

            // 监听对话框显示状态，显示时自动选择第一个
            watch(() => props.visible, (isVisible) => {
                if (isVisible) {
                    autoSelectFirstPlaylist();
                }
            });

            // 组件挂载时自动选择第一个
            onMounted(() => {
                autoSelectFirstPlaylist();
            });

            return {
                selectedPlaylistId,
                selectedPreLists,
                selectedFilesList,
                selectedPlaylist,
                hasSelectedLists,
                selectedFiles: computed(() => props.selectedFiles || []),
                getPreFilesCount,
                getFilesListCount,
                getPlaylistTotalFileCount,
                getMatchedFileCountInPlaylist,
                getMatchedFileCountInPreList,
                getMatchedFileCountInFilesList,
                handleSelectPlaylist,
                handleTogglePreList,
                handleToggleFilesList,
                handleCopy,
                handleRemove,
                handleClose,
            };
        },
        template,
    };
}

