<template>
    <div class="flex gap-4 h-[calc(100vh-220px)] min-w-0 overflow-hidden">
        <!-- 左侧：任务列表 -->
        <div class="w-64 shrink-0 border rounded p-3 flex flex-col">
            <div class="flex items-center justify-between mb-3">
                <h3 class="text-base font-semibold">任务列表</h3>
                <div class="flex items-center gap-1">
                    <el-button type="info" v-bind="smallIconButtonProps" @click="loadTaskList" :loading="loading">
                        <el-icon v-if="!loading">
                            <Refresh />
                        </el-icon>
                    </el-button>
                    <el-button type="success" v-bind="smallIconButtonProps" @click="handleCreateTask"
                        :loading="loading">
                        <el-icon v-if="!loading">
                            <Plus />
                        </el-icon>
                    </el-button>
                </div>
            </div>
            <div v-if="taskList && taskList.length > 0" class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-100">
                <div v-for="task in taskList" :key="task.task_id"
                    class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-15 flex flex-col justify-between"
                    :class="{
                        'border-blue-500 bg-blue-50':
                            currentTask && task.task_id === currentTask.task_id,
                    }" @click="handleViewTask(task.task_id)">
                    <!-- 第一行：名称 -->
                    <div class="flex items-center justify-between gap-2">
                        <div class="text-sm font-medium truncate flex-1 min-w-0" :title="task.name || task.task_id">
                            {{ task.name || task.task_id }}
                        </div>
                    </div>
                    <!-- 第二行：状态、删除按钮 -->
                    <div class="flex items-center justify-between gap-2 min-h-5">
                        <el-tag :type="getStatusTagType(task.status)" size="small"
                            class="h-5! text-xs! w-16 text-center">
                            {{ getStatusText(task.status) }}
                        </el-tag>
                        <div class="flex items-center gap-1 shrink-0">
                            <el-button type="danger" v-bind="smallTextButtonProps"
                                @click.stop="handleDeleteTask(task.task_id)" :disabled="task.status === 'processing'">
                                <el-icon>
                                    <Delete />
                                </el-icon>
                            </el-button>
                        </div>
                    </div>
                </div>
            </div>
            <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400 min-h-100">
                暂无任务，请点击"新建"创建
            </div>
        </div>

        <!-- 右侧：文件信息 + 预览 -->
        <div class="flex-1 min-w-0 border rounded p-3 flex flex-col min-h-0" v-if="currentTask">
            <!-- 上半：文件信息与操作 -->
            <div class="shrink-0 pr-1">
                <h3 class="text-base font-semibold mb-2">文件信息: {{ currentTask.name || currentTask.task_id }}</h3>

                <!-- 任务信息 -->
                <div class="flex items-center gap-4 mb-2">
                    <el-tag :type="getStatusTagType(currentTask.status)" size="small" class="w-16 text-center shrink-0">
                        {{ getStatusText(currentTask.status) }}
                    </el-tag>
                    <el-tooltip v-if="currentTask.error_message" :content="`错误: ${currentTask.error_message}`"
                        placement="top" class="min-w-0 max-w-md">
                        <span class="text-red-500 text-xs truncate block max-w-md cursor-help">
                            错误: {{ currentTask.error_message }}
                        </span>
                    </el-tooltip>
                </div>

                <!-- 文件信息和排版结果水平排列 -->
                <div class="flex gap-2 mb-2">
                    <!-- 上传文件 -->
                    <div class="border rounded p-2 flex-1 min-w-0">
                        <div class="flex items-start justify-between gap-2 min-w-0">
                            <div class="flex items-center gap-2 min-w-0 flex-1">
                                <h4 class="text-xs font-semibold">文件信息</h4>
                            </div>
                            <el-checkbox
                                :model-value="!!currentTask.is_saddle_stitch"
                                size="large"
                                class="saddle-flag-checkbox shrink-0"
                                @change="handleSaddleStitchFlagChange"
                            >
                                骑缝版
                            </el-checkbox>
                        </div>
                        <div v-if="currentTask.uploaded_info" class="text-xs text-gray-600">
                            <div class="truncate" :title="currentTask.uploaded_info.name">
                                {{ currentTask.uploaded_info.name }}
                            </div>
                            <div class="flex items-center gap-2 text-xs text-gray-500">
                                <span>大小: {{ formatSize(currentTask.uploaded_info.size ?? 0) }}</span>
                                <span>修改: {{ formatTime(currentTask.uploaded_info.modified) }}</span>
                            </div>
                        </div>
                        <div v-else class="text-sm text-gray-400">文件信息不可用</div>
                    </div>

                    <!-- 输出文件 -->
                    <div class="border rounded p-2 flex-1 min-w-0">
                        <div class="flex items-center justify-between gap-2">
                            <h4 class="text-xs font-semibold">排版结果</h4>
                            <a v-if="currentTask.output_info" class="text-xs text-blue-600 hover:text-blue-800"
                                :href="getDownloadUrl(currentTask.uploaded_info?.name || currentTask.task_id, 'output')"
                                target="_blank" rel="noopener noreferrer">
                                下载排版结果
                            </a>
                        </div>
                        <template v-if="currentTask.output_info">
                            <div class="text-xs text-gray-600">
                                <div class="truncate" :title="currentTask.output_info.name">
                                    {{ currentTask.output_info.name }}
                                </div>
                                <div class="flex items-center gap-2 text-xs text-gray-500">
                                    <span>大小: {{ formatSize(currentTask.output_info.size ?? 0) }}</span>
                                </div>
                            </div>
                        </template>
                        <div v-else class="text-xs text-gray-400">暂版结果</div>
                    </div>
                </div>

                <!-- 排版进度 -->
                <div v-if="currentTask.status === 'processing'" class="border rounded p-2 mb-2">
                    <h4 class="text-xs font-semibold">排版进度</h4>
                    <el-progress :percentage="50" indeterminate />
                    <div class="text-xs text-gray-400">正在处理中，请稍候...</div>
                </div>
            </div>

            <!-- 下半：PDF 预览 -->
            <div class="flex-1 min-h-0 border-t pt-3 mt-1 flex flex-col">
                <div class="flex items-center justify-between shrink-0 mb-2 h-4">
                    <div class="flex items-center gap-0">
                        <span class="text-sm font-semibold mr-4">PDF 预览</span>
                        <el-button type="success" size="small" plain class="!h-5 !text-xs !px-2 shrink-0"
                            @click="handlePreview(currentTask)" :disabled="!currentTask.uploaded_info || previewLoading"
                            :class="previewMode === 'single' ? '' : '!text-gray-400 !border-gray-300'">
                            {{ previewPages.length > 0 ? "刷新" : "预览" }}
                        </el-button>
                        <el-button v-if="!currentTask.is_saddle_stitch" type="warning" size="small" plain
                            class="!h-5 !text-xs !px-2 shrink-0"
                            @click="handleSaddleStitchPreview(currentTask)"
                            :disabled="!currentTask.uploaded_info || previewLoading"
                            :class="previewMode === 'saddle-stitch' ? '' : '!text-gray-400 !border-gray-300'">
                            骑缝排版
                        </el-button>
                        <el-button type="primary" size="small" plain class="!h-5 !text-xs !px-2 shrink-0"
                            @click="handleBoundPreview(currentTask)"
                            :disabled="!currentTask.uploaded_info || previewLoading"
                            :class="previewMode === 'bound' ? '' : '!text-gray-400 !border-gray-300'">
                            骑缝预览
                        </el-button>
                        <div v-if="!currentTask.is_saddle_stitch && (previewMode === 'saddle-stitch' || previewMode === 'bound') && fillConfigs.length > 0"
                            class="flex items-center gap-1">
                            <span class="text-xs text-gray-500 ml-1">填充:</span>
                            <el-input-number v-for="(_, i) in fillConfigs" :key="i" v-model="fillConfigs[i]"
                                size="small" class="!w-16" :min="1" :max="originalTotalPages + 1"
                                controls-position="right" />
                            <el-button size="small" type="primary" plain class="!h-5 !text-xs !px-2"
                                @click="updateSaddleStitchPreview">
                                更新
                            </el-button>
                            <el-button type="success" size="small" plain class="!h-5 !text-xs !px-2"
                                @click="handleDownloadLayout">
                                生成
                            </el-button>
                        </div>
                    </div>
                    <!-- 单页导航 -->
                    <div v-if="previewMode === 'single' && previewPages.length > 0" class="flex items-center gap-2">
                        <el-button size="small" circle :disabled="previewCurrentPage <= 1" @click="handlePrevPage"
                            class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowLeft />
                            </el-icon>
                        </el-button>
                        <span class="text-xs">{{ previewCurrentPage }} / {{ previewPages.length }}</span>
                        <el-button size="small" circle :disabled="previewCurrentPage >= previewPages.length"
                            @click="handleNextPage" class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowRight />
                            </el-icon>
                        </el-button>
                    </div>
                    <!-- 骑缝导航 -->
                    <div v-else-if="previewMode === 'saddle-stitch' && spreadPages.length > 0"
                        class="flex items-center gap-2">
                        <el-button size="small" circle :disabled="spreadCurrentPage <= 1" @click="handlePrevPage"
                            class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowLeft />
                            </el-icon>
                        </el-button>
                        <span class="text-xs">{{ spreadCurrentPage }} / {{ spreadPages.length }}</span>
                        <el-button size="small" circle :disabled="spreadCurrentPage >= spreadPages.length"
                            @click="handleNextPage" class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowRight />
                            </el-icon>
                        </el-button>
                    </div>
                    <!-- 装订导航 -->
                    <div v-else-if="previewMode === 'bound' && boundPages.length > 0" class="flex items-center gap-2">
                        <el-button size="small" circle :disabled="spreadCurrentPage <= 1" @click="handlePrevPage"
                            class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowLeft />
                            </el-icon>
                        </el-button>
                        <span class="text-xs">{{ spreadCurrentPage }} / {{ boundPages.length }}</span>
                        <el-button size="small" circle :disabled="spreadCurrentPage >= boundPages.length"
                            @click="handleNextPage" class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowRight />
                            </el-icon>
                        </el-button>
                    </div>
                </div>
                <div v-loading="previewLoading" ref="previewAreaRef"
                    class="flex-1 flex items-center justify-center bg-gray-100 rounded min-h-0 overflow-hidden p-2 relative [overflow-anchor:none]"
                    :style="{ '--pdf-ar': pdfPageAspect }">
                    <!-- 左右翻页点击区域（边界禁用，避免无效点击引起滚动/跳动） -->
                    <div v-if="hasPreviewContent"
                        class="absolute left-0 top-0 w-[20%] h-full z-10"
                        :class="canFlipPrev ? 'cursor-pointer' : 'pointer-events-none'"
                        @click.prevent="handlePrevPage"></div>
                    <div v-if="hasPreviewContent"
                        class="absolute right-0 top-0 w-[20%] h-full z-10"
                        :class="canFlipNext ? 'cursor-pointer' : 'pointer-events-none'"
                        @click.prevent="handleNextPage"></div>
                    <!-- 翻书动画容器（勿在此加 filter，会压扁 3D 翻页） -->
                    <div class="flip-perspective flex items-stretch justify-center w-full h-full">
                        <!-- 普通预览（双页）-->
                        <template v-if="previewMode === 'single' && previewPages[previewCurrentPage - 1]">
                            <div class="flip-slot flip-slot-left relative h-full flex-1 min-w-0">
                                <div class="flip-page-stack">
                                    <div class="flip-stage">
                                    <div v-if="flipUnderlayLeft"
                                        class="flip-underlay flip-underlay-left absolute inset-0 z-0 pointer-events-none">
                                        <img v-if="flipUnderlayLeft.leftPageNum === 0" :src="blankPageDataUrl"
                                            class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                        <img v-else-if="flipUnderlayLeft.leftImage" :src="flipUnderlayLeft.leftImage"
                                            class="max-w-full max-h-full object-contain" />
                                    </div>
                                    <div class="flip-page flip-page-left relative z-[1] max-h-full max-w-full"
                                        :class="leftPageAnimeClass">
                                        <div class="flip-page-inner relative">
                                            <div class="flip-face flip-face-front">
                                                <img :src="previewPages[previewCurrentPage - 1].leftImage"
                                                    class="max-w-full max-h-full object-contain" />
                                            </div>
                                            <div class="flip-face flip-face-back">
                                                <template v-if="flipBackSpread">
                                                    <img v-if="flipBackSpread.rightPageNum === 0" :src="blankPageDataUrl"
                                                        class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                                    <img v-else-if="flipBackSpread.rightImage"
                                                        :src="flipBackSpread.rightImage"
                                                        class="max-w-full max-h-full object-contain" />
                                                    <span v-if="flipBackSpread.rightPageNum === 0"
                                                        class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <span class="flip-page-label">{{ leftPageLabel }}</span>
                                </div>
                            </div>
                            <div class="flip-slot flip-slot-right relative h-full flex-1 min-w-0">
                                <div class="flip-page-stack">
                                    <div class="flip-stage">
                                    <div v-if="flipUnderlayRight"
                                        class="flip-underlay flip-underlay-right absolute inset-0 z-0 pointer-events-none">
                                        <img v-if="flipUnderlayRight.rightPageNum === 0" :src="blankPageDataUrl"
                                            class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                        <img v-else-if="flipUnderlayRight.rightImage" :src="flipUnderlayRight.rightImage"
                                            class="max-w-full max-h-full object-contain" />
                                    </div>
                                    <div class="flip-page flip-page-right relative z-[1] max-h-full max-w-full"
                                        :class="rightPageAnimeClass">
                                        <div class="flip-page-inner relative">
                                            <div class="flip-face flip-face-front">
                                                <img v-if="previewPages[previewCurrentPage - 1].rightPageNum === 0"
                                                    :src="blankPageDataUrl"
                                                    class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                                <img v-else :src="previewPages[previewCurrentPage - 1].rightImage"
                                                    class="max-w-full max-h-full object-contain" />
                                                <span v-if="previewPages[previewCurrentPage - 1].rightPageNum === 0"
                                                    class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                            </div>
                                            <div class="flip-face flip-face-back">
                                                <template v-if="flipBackSpread">
                                                    <img v-if="flipBackSpread.leftPageNum === 0" :src="blankPageDataUrl"
                                                        class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                                    <img v-else-if="flipBackSpread.leftImage"
                                                        :src="flipBackSpread.leftImage"
                                                        class="max-w-full max-h-full object-contain" />
                                                    <span v-if="flipBackSpread.leftPageNum === 0"
                                                        class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <span class="flip-page-label">{{ rightPageLabel }}</span>
                                </div>
                            </div>
                        </template>
                        <!-- 骑缝模式（半页翻） -->
                        <template v-else-if="previewMode === 'saddle-stitch' && spreadPages[spreadCurrentPage - 1]">
                            <div class="flip-slot flip-slot-left relative h-full flex-1 min-w-0">
                                <div class="flip-page-stack">
                                    <div class="flip-stage">
                                    <div v-if="flipUnderlayLeft"
                                        class="flip-underlay flip-underlay-left absolute inset-0 z-0 pointer-events-none">
                                        <img v-if="flipUnderlayLeft.leftPageNum === 0" :src="blankPageDataUrl"
                                            class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                        <img v-else-if="flipUnderlayLeft.leftImage" :src="flipUnderlayLeft.leftImage"
                                            class="max-w-full max-h-full object-contain" />
                                        <span v-if="flipUnderlayLeft.leftPageNum === 0"
                                            class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                    </div>
                                    <div class="flip-page flip-page-left relative z-[1] max-h-full max-w-full"
                                        :class="leftPageAnimeClass">
                                        <div class="flip-page-inner relative">
                                            <div class="flip-face flip-face-front">
                                                <img v-if="spreadPages[spreadCurrentPage - 1].leftPageNum === 0"
                                                    :src="blankPageDataUrl"
                                                    class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                                <img v-else :src="spreadPages[spreadCurrentPage - 1].leftImage"
                                                    class="max-w-full max-h-full object-contain" />
                                                <span v-if="spreadPages[spreadCurrentPage - 1].leftPageNum === 0"
                                                    class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                            </div>
                                            <div class="flip-face flip-face-back">
                                                <template v-if="flipBackSpread">
                                                    <img v-if="flipBackSpread.rightPageNum === 0" :src="blankPageDataUrl"
                                                        class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                                    <img v-else-if="flipBackSpread.rightImage"
                                                        :src="flipBackSpread.rightImage"
                                                        class="max-w-full max-h-full object-contain" />
                                                    <span v-if="flipBackSpread.rightPageNum === 0"
                                                        class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <span class="flip-page-label">{{ leftPageLabel }}</span>
                                </div>
                            </div>
                            <div class="flip-slot flip-slot-right relative h-full flex-1 min-w-0">
                                <div class="flip-page-stack">
                                    <div class="flip-stage">
                                    <div v-if="flipUnderlayRight"
                                        class="flip-underlay flip-underlay-right absolute inset-0 z-0 pointer-events-none">
                                        <img v-if="flipUnderlayRight.rightPageNum === 0" :src="blankPageDataUrl"
                                            class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                        <img v-else-if="flipUnderlayRight.rightImage" :src="flipUnderlayRight.rightImage"
                                            class="max-w-full max-h-full object-contain" />
                                        <span v-if="flipUnderlayRight.rightPageNum === 0"
                                            class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                    </div>
                                    <div class="flip-page flip-page-right relative z-[1] max-h-full max-w-full"
                                        :class="rightPageAnimeClass">
                                        <div class="flip-page-inner relative">
                                            <div class="flip-face flip-face-front">
                                                <img v-if="spreadPages[spreadCurrentPage - 1].rightPageNum === 0"
                                                    :src="blankPageDataUrl"
                                                    class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                                <img v-else :src="spreadPages[spreadCurrentPage - 1].rightImage"
                                                    class="max-w-full max-h-full object-contain" />
                                                <span v-if="spreadPages[spreadCurrentPage - 1].rightPageNum === 0"
                                                    class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                            </div>
                                            <div class="flip-face flip-face-back">
                                                <template v-if="flipBackSpread">
                                                    <img v-if="flipBackSpread.leftPageNum === 0" :src="blankPageDataUrl"
                                                        class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                                                    <img v-else-if="flipBackSpread.leftImage"
                                                        :src="flipBackSpread.leftImage"
                                                        class="max-w-full max-h-full object-contain" />
                                                    <span v-if="flipBackSpread.leftPageNum === 0"
                                                        class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <span class="flip-page-label">{{ rightPageLabel }}</span>
                                </div>
                            </div>
                        </template>
                        <!-- 装订预览（骑缝预览） -->
                        <template v-else-if="previewMode === 'bound' && boundPages[spreadCurrentPage - 1]">
                            <div class="flip-slot flip-slot-left relative h-full flex-1 min-w-0">
                                <div class="flip-page-stack">
                                    <div class="flip-stage">
                                    <div v-if="flipUnderlayLeft"
                                        class="flip-underlay flip-underlay-left absolute inset-0 z-0 pointer-events-none">
                                        <template v-if="isFlipTargetCoverLeft"></template>
                                        <template v-else-if="flipUnderlayLeft.leftPageNum === 0">
                                            <img :src="blankPageDataUrl"
                                                class="max-w-full max-h-full object-contain rounded" />
                                            <span
                                                class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                        </template>
                                        <img v-else :src="flipUnderlayLeft.leftImage"
                                            class="max-w-full max-h-full object-contain" />
                                    </div>
                                    <div class="flip-page flip-page-left relative z-[1] max-h-full max-w-full"
                                        :class="leftPageAnimeClass">
                                        <div class="flip-page-inner relative">
                                            <div class="flip-face flip-face-front">
                                                <template v-if="spreadCurrentPage === 1 && boundPages[0].leftPageNum === 0">
                                                </template>
                                                <template v-else-if="boundPages[spreadCurrentPage - 1].leftPageNum === 0">
                                                    <img :src="blankPageDataUrl"
                                                        class="max-w-full max-h-full object-contain rounded" />
                                                    <span
                                                        class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                </template>
                                                <img v-else :src="boundPages[spreadCurrentPage - 1].leftImage"
                                                    class="max-w-full max-h-full object-contain" />
                                            </div>
                                            <div class="flip-face flip-face-back">
                                                <template v-if="flipBackSpread">
                                                    <template v-if="isFlipTargetCoverRight"></template>
                                                    <template v-else-if="flipBackSpread.rightPageNum === 0">
                                                        <img :src="blankPageDataUrl"
                                                            class="max-w-full max-h-full object-contain rounded" />
                                                        <span
                                                            class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                    </template>
                                                    <img v-else :src="flipBackSpread.rightImage"
                                                        class="max-w-full max-h-full object-contain" />
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <span class="flip-page-label">{{ leftPageLabel }}</span>
                                </div>
                            </div>
                            <div class="flip-slot flip-slot-right relative h-full flex-1 min-w-0">
                                <div class="flip-page-stack">
                                    <div class="flip-stage">
                                    <div v-if="flipUnderlayRight"
                                        class="flip-underlay flip-underlay-right absolute inset-0 z-0 pointer-events-none">
                                        <template v-if="isFlipTargetCoverRight"></template>
                                        <template v-else-if="flipUnderlayRight.rightPageNum === 0">
                                            <img :src="blankPageDataUrl"
                                                class="max-w-full max-h-full object-contain rounded" />
                                            <span
                                                class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                        </template>
                                        <img v-else :src="flipUnderlayRight.rightImage"
                                            class="max-w-full max-h-full object-contain" />
                                    </div>
                                    <div class="flip-page flip-page-right relative z-[1] max-h-full max-w-full"
                                        :class="rightPageAnimeClass">
                                        <div class="flip-page-inner relative">
                                            <div class="flip-face flip-face-front">
                                                <template
                                                    v-if="spreadCurrentPage === boundPages.length && boundPages[spreadCurrentPage - 1].rightPageNum === 0">
                                                </template>
                                                <template v-else-if="boundPages[spreadCurrentPage - 1].rightPageNum === 0">
                                                    <img :src="blankPageDataUrl"
                                                        class="max-w-full max-h-full object-contain rounded" />
                                                    <span
                                                        class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                </template>
                                                <img v-else :src="boundPages[spreadCurrentPage - 1].rightImage"
                                                    class="max-w-full max-h-full object-contain" />
                                            </div>
                                            <div class="flip-face flip-face-back">
                                                <template v-if="flipBackSpread">
                                                    <template v-if="isFlipTargetCoverLeft"></template>
                                                    <template v-else-if="flipBackSpread.leftPageNum === 0">
                                                        <img :src="blankPageDataUrl"
                                                            class="max-w-full max-h-full object-contain rounded" />
                                                        <span
                                                            class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                                    </template>
                                                    <img v-else :src="flipBackSpread.leftImage"
                                                        class="max-w-full max-h-full object-contain" />
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <span class="flip-page-label">{{ rightPageLabel }}</span>
                                </div>
                            </div>
                        </template>
                        <span v-else class="text-gray-400 text-sm">点击上方"预览"按钮查看 PDF 内容</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 中间：空状态 -->
        <div class="flex-1 min-w-0 border rounded p-3 flex flex-col" v-else>
            <div class="flex items-center justify-between mb-3 shrink-0">
                <h3 class="text-base font-semibold">文件信息</h3>
            </div>
            <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
                请从左侧选择一个任务查看文件信息
            </div>
        </div>

        <!-- 上传/创建任务对话框 -->
        <el-dialog v-model="createDialogVisible" title="上传 PDF 文件" width="400px" :close-on-click-modal="false"
            @close="handleDialogClose">
            <el-form>
                <el-form-item label="选择文件">
                    <el-upload :auto-upload="false" :on-change="handleFileChange" :show-file-list="false" accept=".pdf">
                        <template #trigger>
                            <el-button type="primary" size="small">选择文件</el-button>
                        </template>
                    </el-upload>
                </el-form-item>
                <div v-if="selectedFile" class="text-sm text-gray-600 mb-2">
                    已选择: {{ selectedFile.name }}
                </div>
                <el-progress v-if="uploadProgress > 0 && uploadProgress < 100" :percentage="uploadProgress" />
                <div v-if="uploadSizeText" class="text-xs text-gray-500 text-right mt-1">
                    已上传: {{ uploadSizeText }}
                </div>
            </el-form>
            <template #footer>
                <el-button @click="handleDialogClose">取消</el-button>
                <el-button type="primary" @click="handleUploadConfirm" :loading="loading" :disabled="!selectedFile">
                    上传
                </el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile } from "element-plus";
import { Refresh, Plus, Delete, ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import { formatSize } from "@/utils/format";
import { logAndNoticeError } from "@/utils/error";
import { loadPdfDocument, renderPdfPageToDataUrl } from "@/utils/pdf-lib";
import { useControllableInterval } from "@/composables/useInterval";
import {
    getPdfLayoutList,
    uploadPdfLayout,
    getPdfLayoutTaskStatus,
    getPdfLayoutDownloadUrl,
    deletePdfLayout,
    savePdfLayout,
    generatePdfLayout,
} from "@/api/api-pdf-layout";
import type { PdfLayoutTask } from "@/types/tools/pdf-layout";

interface SpreadPage {
    id: string;
    leftImage: string;
    rightImage: string;
    leftPageNum: number;
    rightPageNum: number;
}

// 空白页占位图片（初始为空，PDF 加载后按实际页尺寸创建）
const blankPageDataUrl = ref('');
// 预览区尺寸与 PDF 页宽高比（用于小尺寸 PDF 放大铺满）
const previewAreaRef = ref<HTMLElement | null>(null);
const pdfPageAspect = ref(0.707); // width/height，默认约 A4
const previewRenderScale = ref(0.5);

/** 按预览槽位计算渲染缩放：小页放大、大页缩小，兼顾清晰度与内存 */
function computePreviewRenderScale(pageWidthPt: number, pageHeightPt: number): number {
    const el = previewAreaRef.value;
    const slotW = Math.max((el?.clientWidth ?? 800) / 2, 100);
    const slotH = Math.max((el?.clientHeight ?? 600) - 24, 100);
    const fitScale = Math.min(slotW / pageWidthPt, slotH / pageHeightPt);
    const dpr = typeof window !== 'undefined' ? (window.devicePixelRatio || 1) : 1;
    return Math.min(Math.max(fitScale * dpr, 0.5), 2.5);
}

// 根据 PDF 第一页创建同等尺寸的空白 canvas，并记录宽高比 / 渲染缩放
async function initBlankPageImage(pdf: any) {
    try {
        const page = await pdf.getPage(1);
        const base = page.getViewport({ scale: 1 });
        pdfPageAspect.value = base.width / base.height;
        const scale = computePreviewRenderScale(base.width, base.height);
        previewRenderScale.value = scale;

        const viewport = page.getViewport({ scale });
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, viewport.width, viewport.height);
        }
        blankPageDataUrl.value = canvas.toDataURL('image/png');
    } catch {
        // 静默失败，空白页将降级为空字符串
    }
}

/** 骑缝成品页为左右拼接宽页：按半页尺寸初始化空白页与宽高比 */
async function initBlankPageImageFromSaddleSheet(pdf: any) {
    try {
        const page = await pdf.getPage(1);
        const base = page.getViewport({ scale: 1 });
        const halfW = base.width / 2;
        pdfPageAspect.value = halfW / base.height;
        const scale = computePreviewRenderScale(halfW, base.height);
        previewRenderScale.value = scale;

        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.floor(halfW * scale));
        canvas.height = Math.max(1, Math.floor(base.height * scale));
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
        blankPageDataUrl.value = canvas.toDataURL('image/png');
    } catch {
        // 静默失败
    }
}

/** 将骑缝成品的一页（左右拼接）拆成左右半页图片 */
async function renderSaddleSheetHalves(
    page: any,
    scale: number,
): Promise<{ left: string; right: string }> {
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('无法获取 canvas 2d 上下文');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    await page.render({
        canvasContext: ctx,
        viewport,
        canvas: canvas as unknown as HTMLCanvasElement,
    }).promise;

    const halfW = Math.floor(viewport.width / 2);
    const rightW = viewport.width - halfW;
    const h = viewport.height;

    const leftCanvas = document.createElement('canvas');
    leftCanvas.width = halfW;
    leftCanvas.height = h;
    leftCanvas.getContext('2d')!.drawImage(canvas, 0, 0, halfW, h, 0, 0, halfW, h);

    const rightCanvas = document.createElement('canvas');
    rightCanvas.width = rightW;
    rightCanvas.height = h;
    rightCanvas.getContext('2d')!.drawImage(canvas, halfW, 0, rightW, h, 0, 0, rightW, h);

    return {
        left: leftCanvas.toDataURL('image/jpeg', 0.8),
        right: rightCanvas.toDataURL('image/jpeg', 0.8),
    };
}

// 状态映射
const STATUS_MAP: Record<string, { tag: string; text: string }> = {
    uploaded: { tag: "info", text: "已上传" },
    pending: { tag: "info", text: "等待" },
    processing: { tag: "warning", text: "处理" },
    success: { tag: "success", text: "成功" },
    failed: { tag: "danger", text: "失败" },
};

// 按钮样式
const smallIconButtonProps = { size: "small" as const, plain: true, class: "!w-8 !h-6 !p-0" };
const smallTextButtonProps = { size: "small" as const, plain: true, class: "!h-5 !text-xs !px-2" };

// 页面状态
const loading = ref(false);
const taskList = ref<PdfLayoutTask[]>([]);
const currentTask = ref<PdfLayoutTask | null>(null);

// 上传相关
const createDialogVisible = ref(false);
const selectedFile = ref<File | null>(null);
const uploadProgress = ref(0);
const uploadAbortController = ref<AbortController | null>(null);

const uploadSizeText = computed(() => {
    if (!selectedFile.value || uploadProgress.value <= 0) return '';
    const totalKB = Math.round(selectedFile.value.size / 1024);
    const uploadedKB = Math.round(totalKB * uploadProgress.value / 100);
    return `${uploadedKB} KB / ${totalKB} KB`;
});

// 预览相关
const previewMode = ref<'single' | 'saddle-stitch' | 'bound'>('single');
const previewLoading = ref(false);
const previewCurrentPage = ref(1);
const previewPages = ref<SpreadPage[]>([]);
const spreadPages = ref<SpreadPage[]>([]);
const boundPages = ref<SpreadPage[]>([]);
const spreadCurrentPage = ref(1);
const pdfDocCache = shallowRef<any>(null);
const fillConfigs = ref<number[]>([]);
const originalTotalPages = ref(0);
const spreadDataCachedTaskId = ref(''); // 标记当前骑缝数据属于哪个任务
const pageDirection = ref(1); // 翻页方向：1=向前，-1=向后

// 辅助函数
const getStatusTagType = (status: string) => STATUS_MAP[status]?.tag ?? "info";
const getStatusText = (status: string) => STATUS_MAP[status]?.text ?? status;

const confirmAction = (message: string, title = "提示") =>
    ElMessageBox.confirm(message, title, {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
    })
        .then(() => true)
        .catch(() => false);

const withLoading = async (action: () => Promise<void>, errorMessage: string) => {
    try {
        loading.value = true;
        await action();
    } catch (error) {
        logAndNoticeError(error as Error, errorMessage);
    } finally {
        loading.value = false;
    }
};

// 计算属性
// 是否有可翻页的预览内容
const hasPreviewContent = computed(() => {
    if (previewMode.value === 'single') return previewPages.value.length > 0;
    if (previewMode.value === 'saddle-stitch') return spreadPages.value.length > 0;
    if (previewMode.value === 'bound') return boundPages.value.length > 0;
    return false;
});

// ===== 翻书 3D 动画（双面卡牌翻转，完整 180°）=====
const isFlipping = ref(false);
const flipBackSpread = ref<SpreadPage | null>(null);
const flipTargetIndex = ref(-1);
let flipEndTimer: ReturnType<typeof setTimeout> | null = null;

const FLIP_DURATION_MS = 900;

function clearFlipTimers() {
    if (flipEndTimer) { clearTimeout(flipEndTimer); flipEndTimer = null; }
}

// 获取当前模式的页面数组
function getPagesArray(): SpreadPage[] {
    if (previewMode.value === 'single') return previewPages.value;
    if (previewMode.value === 'bound') return boundPages.value;
    return spreadPages.value;
}

// 向前翻只翻右页，向后翻只翻左页（三种预览模式共用半页翻）
const leftPageAnimeClass = computed(() => {
    if (isFlipping.value && pageDirection.value < 0) return 'page-flip-left';
    return '';
});

const rightPageAnimeClass = computed(() => {
    if (isFlipping.value && pageDirection.value > 0) return 'page-flip-right';
    return '';
});

/** 向前翻时，新右页从动画一开始就铺在翻页层下方 */
const flipUnderlayRight = computed(() =>
    isFlipping.value && pageDirection.value > 0 ? flipBackSpread.value : null
);

/** 向后翻时，新左页从动画一开始就铺在翻页层下方 */
const flipUnderlayLeft = computed(() =>
    isFlipping.value && pageDirection.value < 0 ? flipBackSpread.value : null
);

/** 骑缝预览首页左侧 / 末页右侧为透明封面，不是填充空白页 */
const isFlipTargetCoverLeft = computed(() =>
    previewMode.value === 'bound'
    && flipTargetIndex.value === 0
    && flipBackSpread.value?.leftPageNum === 0
);

const isFlipTargetCoverRight = computed(() =>
    previewMode.value === 'bound'
    && flipTargetIndex.value === boundPages.value.length - 1
    && flipBackSpread.value?.rightPageNum === 0
);

/** 当前对开页（页码标签用，与 3D 翻页层解耦） */
const activeSpread = computed(() => {
    if (previewMode.value === 'single') return previewPages.value[previewCurrentPage.value - 1] ?? null;
    if (previewMode.value === 'bound') return boundPages.value[spreadCurrentPage.value - 1] ?? null;
    return spreadPages.value[spreadCurrentPage.value - 1] ?? null;
});

function formatFlipPageLabel(pageNum: number) {
    const n = pageNum === 0 ? originalTotalPages.value : pageNum;
    return n > 0 ? `第 ${n} 页` : '';
}

/** 左侧页码：在翻页层外固定显示，向前翻保持当前页，向后翻显示目标页 */
const leftPageLabel = computed(() => {
    if (flipUnderlayLeft.value) {
        if (isFlipTargetCoverLeft.value) return '';
        return formatFlipPageLabel(flipUnderlayLeft.value.leftPageNum);
    }
    const cur = activeSpread.value;
    if (!cur) return '';
    if (previewMode.value === 'bound' && spreadCurrentPage.value === 1 && cur.leftPageNum === 0) return '';
    return formatFlipPageLabel(cur.leftPageNum);
});

/** 右侧页码：向前翻一开始就显示目标右页 */
const rightPageLabel = computed(() => {
    if (flipUnderlayRight.value) {
        if (isFlipTargetCoverRight.value) return '';
        return formatFlipPageLabel(flipUnderlayRight.value.rightPageNum);
    }
    const cur = activeSpread.value;
    if (!cur) return '';
    if (
        previewMode.value === 'bound'
        && spreadCurrentPage.value === boundPages.value.length
        && cur.rightPageNum === 0
    ) return '';
    return formatFlipPageLabel(cur.rightPageNum);
});

function getCurrentPageIndex(): number {
    if (previewMode.value === 'single') return previewCurrentPage.value;
    return spreadCurrentPage.value;
}

function getMaxPageIndex(): number {
    if (previewMode.value === 'single') return previewPages.value.length;
    if (previewMode.value === 'bound') return boundPages.value.length;
    return spreadPages.value.length;
}

const canFlipPrev = computed(() => hasPreviewContent.value && getCurrentPageIndex() > 1);
const canFlipNext = computed(() => hasPreviewContent.value && getCurrentPageIndex() < getMaxPageIndex());

function advancePageIndex(direction: number) {
    if (previewMode.value === 'single') {
        previewCurrentPage.value += direction;
    } else {
        spreadCurrentPage.value += direction;
    }
}

function triggerFlip(direction: number) {
    if (isFlipping.value) return;
    const current = getCurrentPageIndex();
    const max = getMaxPageIndex();
    if ((direction > 0 && current >= max) || (direction < 0 && current <= 1)) return;

    clearFlipTimers();

    // 准备背面 + 底层内容：目标对开页
    const pages = getPagesArray();
    const targetIdx = current - 1 + direction; // 0-based
    if (targetIdx >= 0 && targetIdx < pages.length) {
        flipBackSpread.value = { ...pages[targetIdx] };
        flipTargetIndex.value = targetIdx;
    } else {
        flipBackSpread.value = null;
        flipTargetIndex.value = -1;
    }

    isFlipping.value = true;
    pageDirection.value = direction;

    // 动画结束后再切页码并清理（底层已提前显示新页，无需中途切换）
    flipEndTimer = setTimeout(() => {
        advancePageIndex(direction);
        isFlipping.value = false;
        flipBackSpread.value = null;
        flipTargetIndex.value = -1;
        flipEndTimer = null;
    }, FLIP_DURATION_MS);
}

// 翻页操作
function handlePrevPage() {
    triggerFlip(-1);
}

function handleNextPage() {
    triggerFlip(1);
}

// 切换预览模式时重置动画状态
watch(previewMode, () => {
    clearFlipTimers();
    isFlipping.value = false;
    flipBackSpread.value = null;
    flipTargetIndex.value = -1;
});

// 应用任务数据到当前视图
const applyTask = (task: PdfLayoutTask) => {
    currentTask.value = task;
    const index = taskList.value.findIndex(item => item.task_id === task.task_id);
    if (index >= 0) taskList.value[index] = { ...task };
};

// 加载任务列表
const loadTaskList = () =>
    withLoading(async () => {
        const response = await getPdfLayoutList();
        if (response.code === 0) {
            const tasks = (response.data || []) as PdfLayoutTask[];
            taskList.value = tasks;
            if (!currentTask.value && taskList.value.length) {
                await syncTask(taskList.value[0].task_id);
            }
        } else {
            ElMessage.error(response.msg || "获取任务列表失败");
        }
    }, "获取任务列表失败");

// 同步任务信息
const syncTask = async (taskId?: string) => {
    const id = taskId ?? currentTask.value?.task_id;
    if (!id) return;
    try {
        const response = await getPdfLayoutTaskStatus(id);
        if (response.code === 0) {
            applyTask(response.data as PdfLayoutTask);
        }
    } catch (error) {
        logAndNoticeError(error as Error, "获取任务信息失败");
    }
};

// 查看任务
const handleViewTask = async (taskId: string) => {
    await syncTask(taskId);
};

// 创建任务（打开上传对话框）
const handleCreateTask = () => {
    selectedFile.value = null;
    uploadProgress.value = 0;
    uploadAbortController.value = new AbortController();
    createDialogVisible.value = true;
};

const handleDialogClose = () => {
    uploadAbortController.value?.abort();
    uploadAbortController.value = null;
    selectedFile.value = null;
    uploadProgress.value = 0;
    createDialogVisible.value = false;
};

const handleFileChange = (file: UploadFile) => {
    if (file.raw) {
        selectedFile.value = file.raw;
        uploadProgress.value = 0;
    }
};

// 上传确认
const handleUploadConfirm = async () => {
    if (!selectedFile.value) {
        ElMessage.warning("请选择文件");
        return;
    }
    await withLoading(async () => {
        uploadProgress.value = 0;
        const signal = uploadAbortController.value?.signal;
        try {
            const response = await uploadPdfLayout(selectedFile.value!, p => {
                uploadProgress.value = p;
            }, signal);
            if (response.code === 0) {
                uploadProgress.value = 100;
                ElMessage.success("文件上传成功");
                createDialogVisible.value = false;
                selectedFile.value = null;
                await loadTaskList();
                const task = response.data as PdfLayoutTask;
                if (task?.task_id) await syncTask(task.task_id);
            } else {
                ElMessage.error(response.msg || "文件上传失败");
            }
        } catch (err: any) {
            if (err?.name === 'AbortError' || err?.code === 'ERR_CANCELED') {
                // 用户取消上传，静默处理
                return;
            }
            throw err;
        }
    }, "文件上传失败");
};

// 删除任务
const handleDeleteTask = async (taskId: string) => {
    if (!(await confirmAction("确定要删除该任务吗？"))) return;
    await withLoading(async () => {
        const response = await deletePdfLayout(taskId);
        if (response.code === 0) {
            ElMessage.success("任务删除成功");
            taskList.value = (await getPdfLayoutList()).data as PdfLayoutTask[] || [];
            if (currentTask.value?.task_id !== taskId) return;
            if (taskList.value.length) await syncTask(taskList.value[0].task_id);
            else currentTask.value = null;
        } else {
            ElMessage.error(response.msg || "删除任务失败");
        }
    }, "删除任务失败");
};

// 轮询
const { stop: stopPolling } = useControllableInterval(async () => {
    const task = currentTask.value;
    if (!task?.task_id) return stopPolling();
    try {
        const response = await getPdfLayoutTaskStatus(task.task_id);
        if (response.code === 0) {
            applyTask(response.data as PdfLayoutTask);
            if (response.data.status !== "processing") {
                taskList.value = (await getPdfLayoutList()).data as PdfLayoutTask[] || [];
                stopPolling();
            }
        }
    } catch (error) {
        logAndNoticeError(error as Error, "刷新任务状态失败");
    }
}, 1000);

// 下载 URL
const getDownloadUrl = (filename: string, type: "uploaded" | "output") => {
    return getPdfLayoutDownloadUrl(filename, type);
};

// 预览 PDF（双页预览）
const handlePreview = async (item: PdfLayoutTask) => {
    if (!item.uploaded_info) {
        ElMessage.warning("文件不存在");
        return;
    }

    previewMode.value = 'single';
    previewLoading.value = true;
    previewCurrentPage.value = 1;
    previewPages.value = [];

    try {
        const url = getPdfLayoutDownloadUrl(item.uploaded_info.name, "uploaded");
        if (!url) {
            ElMessage.error("无法获取文件地址");
            previewLoading.value = false;
            return;
        }

        console.time('loadPdf');
        const pdf = await loadPdfDocument(url);
        console.timeEnd('loadPdf');
        await initBlankPageImage(pdf);
        const scale = previewRenderScale.value;

        const totalPages = pdf.numPages;
        console.log(`PDF 页数: ${totalPages}, 文件: ${item.uploaded_info.name}, scale: ${scale}`);
        originalTotalPages.value = totalPages;

        // 并行渲染所有 spread
        console.time('renderAllPages');
        const spreadPromises: Promise<SpreadPage>[] = [];
        for (let i = 1; i <= totalPages; i += 2) {
            const pageIdx = i;
            spreadPromises.push(
                (async () => {
                    const leftImg = await renderPdfPageToDataUrl(await pdf.getPage(pageIdx), {
                        scale,
                        mimeType: "image/jpeg",
                        quality: 0.7,
                    });

                    let rightImg = '';
                    let rightNum = 0;
                    if (pageIdx + 1 <= totalPages) {
                        rightImg = await renderPdfPageToDataUrl(await pdf.getPage(pageIdx + 1), {
                            scale,
                            mimeType: "image/jpeg",
                            quality: 0.7,
                        });
                        rightNum = pageIdx + 1;
                    }

                    return {
                        id: `${pageIdx}-${pageIdx + 1}`,
                        leftImage: leftImg,
                        rightImage: rightImg,
                        leftPageNum: pageIdx,
                        rightPageNum: rightNum,
                    } as SpreadPage;
                })()
            );
        }

        previewPages.value = await Promise.all(spreadPromises);
        console.timeEnd('renderAllPages');
        // 加载完成后释放 PDF 文档以释放内存
        await pdf.destroy();
    } catch (error) {
        logAndNoticeError(error as Error, "加载 PDF 预览失败");
        previewPages.value = [];
    } finally {
        previewLoading.value = false;
    }
};

// 骑缝排版算法：生成对开页序列
function generateSaddleStitchSpreads(effectiveCount: number): [number, number][] {
    const spreads: [number, number][] = [];
    for (let s = 0; s < effectiveCount / 4; s++) {
        spreads.push([effectiveCount - 2 * s, 2 * s + 1]);
        spreads.push([2 * s + 2, effectiveCount - 2 * s - 1]);
    }
    return spreads;
}

// 构建有效页面数据：0=空白页，>0=原始页码，自动补齐到4的倍数
// insertAt: 在指定页码前插入空白页（>totalPages 表示在末尾追加）
function buildEffectivePages(totalPages: number, insertAt: number[]): number[] {
    const pages: number[] = [];
    for (let i = 1; i <= totalPages; i++) {
        const count = insertAt.filter(p => p === i).length;
        for (let b = 0; b < count; b++) pages.push(0);
        pages.push(i);
    }
    // 末尾追加空白（填值 > totalPages）
    const trailing = insertAt.filter(p => p > totalPages).length;
    for (let b = 0; b < trailing; b++) pages.push(0);
    const padded = Math.ceil(pages.length / 4) * 4;
    while (pages.length < padded) pages.push(0);
    return pages;
}

// 初始化填充配置：需要几页就生成几个默认值（全部在末页后）
function initFillConfigs(totalPages: number): number[] {
    const needed = Math.ceil(totalPages / 4) * 4 - totalPages;
    return needed > 0 ? Array(needed).fill(totalPages + 1) : [];
}

// 骑缝排版（加载并初始化填充配置）
const handleSaddleStitchPreview = async (item: PdfLayoutTask) => {
    if (!item.uploaded_info) {
        ElMessage.warning("文件不存在");
        return;
    }

    // 如果骑缝数据已为当前任务生成过，直接切换模式不重新计算
    if (spreadPages.value.length > 0 && pdfDocCache.value && spreadDataCachedTaskId.value === item.task_id) {
        previewMode.value = 'saddle-stitch';
        spreadCurrentPage.value = 1;
        return;
    }

    previewLoading.value = true;
    previewMode.value = 'saddle-stitch';
    spreadPages.value = [];
    spreadCurrentPage.value = 1;

    try {
        const url = getPdfLayoutDownloadUrl(item.uploaded_info.name, "uploaded");
        if (!url) {
            ElMessage.error("无法获取文件地址");
            previewLoading.value = false;
            return;
        }

        const pdf = await loadPdfDocument(url);
        await initBlankPageImage(pdf);
        const totalPages = pdf.numPages;
        originalTotalPages.value = totalPages;
        fillConfigs.value = (item.fill_configs && item.fill_configs.length > 0)
            ? [...item.fill_configs]
            : initFillConfigs(totalPages);
        pdfDocCache.value = pdf;
        spreadDataCachedTaskId.value = item.task_id;
        await renderSaddleStitchPreview();
    } catch (error) {
        logAndNoticeError(error as Error, "加载骑缝排版失败");
        spreadPages.value = [];
    } finally {
        previewLoading.value = false;
    }
};

// 渲染骑缝预览（使用当前 fillConfigs）
const renderSaddleStitchPreview = async (skipLoading = false) => {
    const pdf = pdfDocCache.value;
    if (!pdf) return;

    if (!skipLoading) previewLoading.value = true;
    spreadPages.value = [];
    spreadCurrentPage.value = 1;

    try {
        const effectiveData = buildEffectivePages(originalTotalPages.value, fillConfigs.value);
        const spreads = generateSaddleStitchSpreads(effectiveData.length);

        // 并行渲染所有对开页
        const spreadPromises: Promise<SpreadPage>[] = spreads.map(async ([leftIdx, rightIdx]) => {
            const leftPageNum = effectiveData[leftIdx - 1];
            const rightPageNum = effectiveData[rightIdx - 1];

            const scale = previewRenderScale.value;
            let leftImg = '';
            if (leftPageNum > 0) {
                leftImg = await renderPdfPageToDataUrl(await pdf.getPage(leftPageNum), {
                    scale, mimeType: "image/jpeg", quality: 0.8,
                });
            }

            let rightImg = '';
            if (rightPageNum > 0) {
                rightImg = await renderPdfPageToDataUrl(await pdf.getPage(rightPageNum), {
                    scale, mimeType: "image/jpeg", quality: 0.8,
                });
            }

            return {
                id: `${leftIdx}-${rightIdx}`,
                leftImage: leftImg,
                rightImage: rightImg,
                leftPageNum,
                rightPageNum,
            } as SpreadPage;
        });

        spreadPages.value = await Promise.all(spreadPromises);
    } catch (error) {
        logAndNoticeError(error as Error, "渲染骑缝预览失败");
        spreadPages.value = [];
    } finally {
        if (!skipLoading) previewLoading.value = false;
    }
};

// 生成阅读顺序对开页（空白-1, 2-3, 4-5...）
function generateBoundSpreads(effectiveData: number[]): [number, number][] {
    const spreads: [number, number][] = [];
    const n = effectiveData.length;
    if (n === 0) return spreads;

    // 第一个对开：[空白, 第1页]
    spreads.push([0, effectiveData[0]]);

    // 剩余页顺序配对（2-3, 4-5...）
    for (let i = 1; i < n; i += 2) {
        const right = i + 1 < n ? effectiveData[i + 1] : 0;
        spreads.push([effectiveData[i], right]);
    }

    return spreads;
}

// 渲染装订预览（从骑缝排版数据提取，按阅读顺序重排）
const renderBoundPreview = async (skipLoading = false) => {
    const pdf = pdfDocCache.value;
    if (!pdf) return;

    if (!skipLoading) previewLoading.value = true;
    boundPages.value = [];
    spreadCurrentPage.value = 1;

    try {
        // 从已渲染的 spreadPages 建立页码→图片映射
        const pageImageMap = new Map<number, string>();
        for (const sp of spreadPages.value) {
            if (sp.leftPageNum > 0) pageImageMap.set(sp.leftPageNum, sp.leftImage);
            if (sp.rightPageNum > 0) pageImageMap.set(sp.rightPageNum, sp.rightImage);
        }

        const effectiveData = buildEffectivePages(originalTotalPages.value, fillConfigs.value);
        const boundSpreads = generateBoundSpreads(effectiveData);

        for (const [leftNum, rightNum] of boundSpreads) {
            boundPages.value.push({
                id: `${leftNum}-${rightNum}`,
                leftImage: pageImageMap.get(leftNum) || '',
                rightImage: pageImageMap.get(rightNum) || '',
                leftPageNum: leftNum,
                rightPageNum: rightNum,
            });
        }

    } catch (error) {
        logAndNoticeError(error as Error, "渲染装订预览失败");
        boundPages.value = [];
    } finally {
        if (!skipLoading) previewLoading.value = false;
    }
};

// 装订预览（复用骑缝排版数据，按阅读顺序展示）
const handleBoundPreview = async (item: PdfLayoutTask) => {
    if (!item.uploaded_info) {
        ElMessage.warning("文件不存在");
        return;
    }
    // 已是骑缝成品：原始 PDF 即拼版页，拆半后按阅读顺序预览
    if (item.is_saddle_stitch) {
        await loadBoundPreviewFromSaddlePdf(item);
        return;
    }
    if (!pdfDocCache.value || spreadDataCachedTaskId.value !== item.task_id || spreadPages.value.length === 0) {
        await handleSaddleStitchPreview(item);
    }
    previewMode.value = 'bound';
    spreadCurrentPage.value = 1;
    await renderBoundPreview();
};

/** 把已是骑缝成品的原始 PDF 拆页后，按阅读顺序做装订预览 */
const loadBoundPreviewFromSaddlePdf = async (item: PdfLayoutTask) => {
    previewLoading.value = true;
    previewMode.value = 'bound';
    boundPages.value = [];
    spreadPages.value = [];
    fillConfigs.value = [];
    spreadCurrentPage.value = 1;

    try {
        const url = getPdfLayoutDownloadUrl(item.uploaded_info!.name, "uploaded");
        if (!url) {
            ElMessage.error("无法获取文件地址");
            return;
        }

        const pdf = await loadPdfDocument(url);
        await initBlankPageImageFromSaddleSheet(pdf);
        pdfDocCache.value = pdf;
        spreadDataCachedTaskId.value = item.task_id;

        const numSheets = pdf.numPages;
        const effectiveCount = numSheets * 2;
        originalTotalPages.value = effectiveCount;

        const spreads = generateSaddleStitchSpreads(effectiveCount);
        const pageImageMap = new Map<number, string>();
        const scale = previewRenderScale.value;

        const halfResults = await Promise.all(
            spreads.map(async ([leftIdx, rightIdx], sheetIndex) => {
                const page = await pdf.getPage(sheetIndex + 1);
                const halves = await renderSaddleSheetHalves(page, scale);
                return { leftIdx, rightIdx, halves };
            }),
        );

        for (const { leftIdx, rightIdx, halves } of halfResults) {
            pageImageMap.set(leftIdx, halves.left);
            pageImageMap.set(rightIdx, halves.right);
        }

        const effectiveData = Array.from({ length: effectiveCount }, (_, i) => i + 1);
        const boundSpreads = generateBoundSpreads(effectiveData);
        boundPages.value = boundSpreads.map(([leftNum, rightNum]) => ({
            id: `${leftNum}-${rightNum}`,
            leftImage: leftNum > 0 ? (pageImageMap.get(leftNum) || '') : '',
            rightImage: rightNum > 0 ? (pageImageMap.get(rightNum) || '') : '',
            leftPageNum: leftNum,
            rightPageNum: rightNum,
        }));
    } catch (error) {
        logAndNoticeError(error as Error, "加载骑缝成品预览失败");
        boundPages.value = [];
    } finally {
        previewLoading.value = false;
    }
};

// 按当前填充配置重新渲染骑缝预览
const updateSaddleStitchPreview = async () => {
    const task = currentTask.value;
    if (!task) return;
    previewLoading.value = true;
    try {
        await savePdfLayout(task.task_id, fillConfigs.value, !!task.is_saddle_stitch);
        await renderSaddleStitchPreview(true);
        // 如果在骑缝预览模式，同步刷新 boundPages
        if (previewMode.value === 'bound') {
            await renderBoundPreview(true);
        }
    } finally {
        previewLoading.value = false;
    }
};

// 切换骑缝版标记并保存到存档（表示 PDF 已是骑缝成品）
const handleSaddleStitchFlagChange = async (val: string | number | boolean) => {
    const task = currentTask.value;
    if (!task) return;
    const checked = !!val;
    try {
        const result = await savePdfLayout(
            task.task_id,
            task.fill_configs || fillConfigs.value || [],
            checked,
        );
        if (result.code !== 0) {
            ElMessage.error(result.msg || "保存骑缝版标记失败");
            return;
        }
        applyTask({ ...task, is_saddle_stitch: checked });
        // 已是骑缝成品时退出骑缝排版模式
        if (checked && previewMode.value === 'saddle-stitch') {
            previewMode.value = 'single';
        }
    } catch (error) {
        logAndNoticeError(error as Error, "保存骑缝版标记失败");
    }
};

// 生成并下载骑缝排版 PDF
const handleDownloadLayout = async () => {
    const task = currentTask.value;
    if (!task) return;
    if (previewLoading.value) {
        ElMessage.warning("正在渲染中，请稍候");
        return;
    }

    previewLoading.value = true;
    try {
        // 先保存填充配置
        const saveResult = await savePdfLayout(task.task_id, fillConfigs.value, !!task.is_saddle_stitch);
        if (saveResult.code !== 0) {
            ElMessage.error(saveResult.msg || "保存填充配置失败");
            return;
        }
        // 再生成 PDF
        const response = await generatePdfLayout(task.task_id);
        if (response.code !== 0 || !response.data) {
            ElMessage.error(response.msg || "生成骑缝 PDF 失败");
            return;
        }

        const result = response.data;
        const filename = result.output_info?.name || result.task_id;
        if (filename) {
            const url = getPdfLayoutDownloadUrl(filename, 'output');
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            ElMessage.success("骑缝排版 PDF 已生成并开始下载");
        }
    } catch (error) {
        logAndNoticeError(error as Error, "保存骑缝排版 PDF 失败");
    } finally {
        previewLoading.value = false;
    }
};

const formatTime = (timestamp?: number) => {
    if (!timestamp) return "-";
    return new Date(timestamp * 1000).toLocaleString();
};

// 生命周期
onMounted(loadTaskList);
onBeforeUnmount(() => {
    stopPolling();
    clearFlipTimers();
});
</script>

<style scoped>
/* ===== 翻书 3D 透视容器 ===== */
.flip-perspective {
    perspective: 1200px;
    transform-style: preserve-3d;
}

/* 左右半页槽位：上方翻页舞台 + 下方固定页码 */
.flip-slot {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    container-type: size;
}

.flip-slot-left {
    justify-content: flex-end;
}

.flip-slot-right {
    justify-content: flex-start;
}

/* 正在翻的那一侧整槽抬高，避免翻过中缝后沉到对页下面 */
.flip-slot:has(.page-flip-right),
.flip-slot:has(.page-flip-left) {
    z-index: 20;
}

/* 图片+页码同宽一列，页码相对 PDF 居中 */
.flip-page-stack {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    max-width: 100%;
    max-height: 100%;
    min-height: 0;
    gap: 0.25rem;
}

/* 仅图片参与 3D；underlay 与 flip-page 叠同一格 */
.flip-stage {
    position: relative;
    display: grid;
    align-items: center;
    flex: 0 1 auto;
    min-height: 0;
    min-width: 0;
    max-width: 100%;
    max-height: calc(100cqh - 1.5rem);
    transform-style: preserve-3d;
}

.flip-slot-left .flip-stage {
    justify-items: end;
}

.flip-slot-right .flip-stage {
    justify-items: start;
}

.flip-stage > .flip-underlay,
.flip-stage > .flip-page {
    grid-area: 1 / 1;
}

.flip-page-label {
    flex-shrink: 0;
    position: relative;
    z-index: 3;
    font-size: 0.75rem;
    line-height: 1;
    color: #9ca3af;
    text-align: center;
    white-space: nowrap;
    height: 1rem; /* 固定占位，避免末页无页码时高度塌缩导致整体下移 */
}

/* 页面外层：尺寸由 PDF 图决定，不超过槽位 */
.flip-page {
    position: relative;
    z-index: 2;
    max-width: 100%;
    max-height: 100%;
    width: fit-content;
    height: fit-content;
    transform-style: preserve-3d;
}

/* 左页以书脊（右边缘）为轴翻转 */
.flip-page-left {
    transform-origin: right center;
}

/* 右页以书脊（左边缘）为轴翻转 */
.flip-page-right {
    transform-origin: left center;
}

/* 页面内层（承载正反两面） */
.flip-page-inner {
    position: relative;
    width: fit-content;
    height: fit-content;
    max-width: 100%;
    max-height: 100%;
    transform-style: preserve-3d;
}

/* 正面：参与文档流，决定翻页卡片真实大小（= PDF 页） */
.flip-face-front {
    position: relative;
    display: block;
    width: fit-content;
    max-width: 100%;
    max-height: 100%;
    backface-visibility: hidden;
    background: transparent;
}

/* 背面：叠在正面同尺寸上 */
.flip-face-back {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    backface-visibility: hidden;
    transform: rotateY(180deg);
    background: #fff;
}

/* 按槽位与 PDF 宽高比缩放（小页放大、大页缩小），贴合书脊 */
.flip-face img,
.flip-underlay img {
    display: block;
    width: min(100cqw, calc((100cqh - 1.5rem) * var(--pdf-ar, 0.707)));
    height: min(calc(100cqh - 1.5rem), calc(100cqw / var(--pdf-ar, 0.707)));
    object-fit: contain;
}

/* 预加载页始终在翻页卡下方 */
.flip-underlay {
    position: relative !important;
    inset: auto !important;
    z-index: 0 !important;
    display: flex;
    align-items: center;
    justify-content: center;
    width: fit-content;
    height: fit-content;
    max-width: 100%;
    max-height: 100%;
    pointer-events: none;
    transform: translateZ(-1px);
}

.flip-underlay-left {
    justify-content: flex-end;
}

.flip-underlay-right {
    justify-content: flex-start;
}

/* 翻页中再抬一层，并带一点 translateZ，保证盖过对页 */
.page-flip-left,
.page-flip-right {
    z-index: 10 !important;
}

/* ===== 向前翻页（下一页）：右页绕左边缘旋转 -180° ===== */
.page-flip-right {
    animation: flipRight 0.9s cubic-bezier(0.645, 0.045, 0.355, 1) forwards;
}

@keyframes flipRight {
    from {
        transform: translateZ(2px) rotateY(0deg);
    }

    to {
        transform: translateZ(2px) rotateY(-180deg);
    }
}

/* ===== 向后翻页（上一页）：左页绕右边缘旋转 180° ===== */
.page-flip-left {
    animation: flipLeft 0.9s cubic-bezier(0.645, 0.045, 0.355, 1) forwards;
}

@keyframes flipLeft {
    from {
        transform: translateZ(2px) rotateY(0deg);
    }

    to {
        transform: translateZ(2px) rotateY(180deg);
    }
}

.saddle-flag-checkbox :deep(.el-checkbox__inner) {
    width: 18px;
    height: 18px;
}

.saddle-flag-checkbox :deep(.el-checkbox__inner::after) {
    left: 6px;
    height: 9px;
    width: 4px;
}

.saddle-flag-checkbox :deep(.el-checkbox__label) {
    font-size: 14px;
    font-weight: 600;
}
</style>
