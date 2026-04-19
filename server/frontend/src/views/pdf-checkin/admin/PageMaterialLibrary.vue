<template>
  <div class="material-library-page">
    <h1 class="page-title">资料库管理</h1>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab">
      <el-tab-pane label="PDF课件" name="pdf">
        <!-- 操作栏 -->
        <div class="toolbar">
          <div class="filter-controls">
            <el-input
              v-model="pdfSearchName"
              placeholder="按文件名称搜索"
              clearable
              style="width: 200px"
            />
            <el-date-picker
              v-model="pdfDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
            />
            <el-button type="primary" @click="loadPdfList">筛选</el-button>
            <el-button @click="resetPdfFilter">重置</el-button>
          </div>
          <div class="action-buttons">
            <el-button type="success" @click="showCreateFolderDialog">
              <el-icon><FolderAdd /></el-icon>
              新建文件夹
            </el-button>
            <el-button type="warning" @click="showMoveFileDialog">
              移动到文件夹
            </el-button>
            <el-button type="primary" @click="showUploadDialog">
              <el-icon><Upload /></el-icon>
              上传文件
            </el-button>
          </div>
        </div>

        <!-- 文件夹列表 -->
        <el-table v-if="pdfFolders.length > 0" :data="pdfFolders" border stripe style="margin-bottom: 20px">
          <el-table-column prop="name" label="文件夹名称" min-width="200">
            <template #default="{ row }">
              <div class="folder-name-link" @click="viewFolder(row, 'pdf')">
                <el-icon style="margin-right: 8px; vertical-align: middle;"><Folder /></el-icon>
                {{ row.name }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="fileCount" label="文件数量" width="120" />
          <el-table-column prop="createTime" label="创建时间" width="180" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewFolder(row, 'pdf')">
                查看
              </el-button>
              <el-button link type="primary" @click="editFolder(row)">
                重命名
              </el-button>
              <el-button link type="danger" @click="deleteFolder(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- PDF文件列表 -->
        <el-table
          ref="pdfTableRef"
          :data="pdfList"
          border
          stripe
          @selection-change="handlePdfSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="文件名称" min-width="200">
            <template #default="{ row }">
              <el-icon v-if="row.folderId" style="margin-right: 8px; vertical-align: middle;"><Document /></el-icon>
              {{ row.name }}
            </template>
          </el-table-column>
          <el-table-column prop="size" label="文件大小" width="120">
            <template #default="{ row }">
              {{ formatFileSize(row.size) }}
            </template>
          </el-table-column>
          <el-table-column prop="uploadTime" label="上传时间" width="180" />
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="editPdfCourseware(row)">
                编辑
              </el-button>
              <el-button link type="primary" @click="viewPdf(row)">
                查看
              </el-button>
              <el-button link type="danger" @click="deletePdf(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传PDF课件"
      width="500px"
    >
      <el-form :model="uploadForm" label-width="80px">
        <!-- 上传方式选择 -->
        <el-form-item label="上传方式">
          <el-radio-group v-model="uploadMode">
            <el-radio value="local">本地上传</el-radio>
            <el-radio value="cloud">云端选择</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 本地上传 -->
        <el-form-item v-if="uploadMode === 'local'" label="选择文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept=".pdf"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                只能上传PDF文件
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 云端选择 -->
        <el-form-item v-if="uploadMode === 'cloud'" label="选择文件">
          <el-button type="primary" @click="openCloudFileDialog">
            <el-icon><FolderOpened /></el-icon>
            从云端选择
          </el-button>
          <div v-if="uploadForm.cloudPath" class="text-sm text-gray-600 mt-2">
            已选择：{{ uploadForm.cloudPath }}
          </div>
        </el-form-item>

        <el-form-item label="文件名称">
          <el-input v-model="uploadForm.name" placeholder="请输入文件名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入文件描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload">确认上传</el-button>
      </template>
    </el-dialog>

    <!-- 编辑描述对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑描述"
      width="500px"
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="文件名称">
          <el-input v-model="editForm.name" disabled />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入文件描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmEdit">确认</el-button>
      </template>
    </el-dialog>

    <!-- 云端文件选择对话框 -->
    <FileDialog
      v-model:visible="cloudFileDialogVisible"
      title="选择PDF文件"
      extensions=".pdf"
      mode="file"
      @confirm="handleCloudFileConfirm"
    />

    <!-- 新建文件夹对话框 -->
    <el-dialog
      v-model="createFolderDialogVisible"
      title="新建文件夹"
      width="450px"
    >
      <el-form :model="createFolderForm" label-width="100px">
        <el-form-item label="文件夹名称">
          <el-input
            v-model="createFolderForm.name"
            placeholder="请输入文件夹名称"
            @keyup.enter="confirmCreateFolder"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="createFolderForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createFolderDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmCreateFolder">确认</el-button>
      </template>
    </el-dialog>

    <!-- 重命名文件夹对话框 -->
    <el-dialog
      v-model="renameFolderDialogVisible"
      title="重命名文件夹"
      width="450px"
    >
      <el-form :model="renameFolderForm" label-width="100px">
        <el-form-item label="文件夹名称">
          <el-input
            v-model="renameFolderForm.name"
            placeholder="请输入文件夹名称"
            @keyup.enter="confirmRenameFolder"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameFolderDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRenameFolder">确认</el-button>
      </template>
    </el-dialog>

    <!-- 移动文件到文件夹对话框 -->
    <el-dialog
      v-model="moveFileDialogVisible"
      title="移动到文件夹"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item label="目标文件夹">
          <el-select v-model="targetFolderId" placeholder="请选择文件夹" style="width: 100%">
            <el-option
              v-for="folder in pdfFolders"
              :key="folder.id"
              :label="folder.name"
              :value="folder.id"
            >
              <span>{{ folder.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ folder.fileCount }} 个文件</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="已选文件">
          <div class="text-sm text-gray-600">
            {{ selectedPdfFiles.length }} 个文件
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveFileDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmMoveFiles">确认移动</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Upload, FolderOpened, Folder, FolderAdd, Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FileDialog from '@/views/dialogs/FileDialog.vue'

interface FileItem {
  id: string
  name: string
  size: number
  uploadTime: string
  description?: string
  relatedPdf?: string
  cloudPath?: string
  folderId?: string // 所属文件夹ID
}

interface FolderItem {
  id: string
  name: string
  fileCount: number
  createTime: string
  description?: string
}

const router = useRouter()

// 表格引用
const pdfTableRef = ref()
const activeTab = ref('pdf')

// PDF相关
const pdfSearchName = ref('')
const pdfDateRange = ref<string[]>([])
const pdfFolders = ref<FolderItem[]>([
  {
    id: 'folder-pdf-1',
    name: '语文课文',
    fileCount: 5,
    createTime: '2024-01-10 09:00:00',
    description: '初中语文课文集合'
  }
])
const pdfList = ref<FileItem[]>([
  {
    id: 'sample-pdf-1',
    name: '春.pdf',
    size: 1024000,
    uploadTime: '2024-01-15 10:30:00',
    description: '朱自清散文样例'
  }
])

// 音频文件夹和文件
const audioFolders = ref<FolderItem[]>([])
const audioList = ref<FileItem[]>([])

// 保存数据到 localStorage
const saveDataToLocalStorage = () => {
  const data = {
    pdf: pdfFolders.value,
    audio: audioFolders.value,
    pdfFiles: pdfList.value,
    audioFiles: audioList.value
  }
  localStorage.setItem('materialFolders', JSON.stringify(data))
}
// 上传相关
const uploadDialogVisible = ref(false)
const uploadMode = ref<'local' | 'cloud'>('local')
const uploadForm = reactive({
  name: '',
  description: '',
  file: null as File | null,
  cloudPath: ''
})

// 云端文件选择
const cloudFileDialogVisible = ref(false)
const openCloudFileDialog = () => {
  cloudFileDialogVisible.value = true
}

const handleCloudFileConfirm = (filePaths: string[]) => {
  if (filePaths.length > 0) {
    uploadForm.cloudPath = filePaths[0]
    if (!uploadForm.name) {
      const fileName = filePaths[0].split('/').pop() || ''
      uploadForm.name = fileName.replace(/\.[^/.]+$/, '')
    }
    ElMessage.success('已选择云端文件')
  }
}

// 编辑相关
const editDialogVisible = ref(false)
const editForm = reactive({
  id: '',
  name: '',
  description: ''
})

// 文件夹相关
const createFolderDialogVisible = ref(false)
const renameFolderDialogVisible = ref(false)
const currentEditingFolder = ref<FolderItem | null>(null)

const createFolderForm = reactive({
  name: '',
  description: ''
})

const renameFolderForm = reactive({
  name: ''
})

// 选中的文件
const selectedPdfFiles = ref<FileItem[]>([])

// 移动文件到文件夹对话框
const moveFileDialogVisible = ref(false)
const targetFolderId = ref<string>('')

// 加载PDF列表
const loadPdfList = () => {
  // 实际项目中调用API，这里仅做演示
}

// 重置PDF筛选
const resetPdfFilter = () => {
  pdfSearchName.value = ''
  pdfDateRange.value = []
}

// 显示上传对话框
const showUploadDialog = () => {
  uploadMode.value = 'local'
  uploadForm.name = ''
  uploadForm.description = ''
  uploadForm.file = null
  uploadForm.cloudPath = ''
  uploadDialogVisible.value = true
}

// 文件选择变化
const handleFileChange = (file: { status?: string; raw?: File; name: string }) => {
  if (file.status === 'removed') {
    uploadForm.file = null
    return
  }
  if (file.raw) {
    uploadForm.file = file.raw
  }
  if (!uploadForm.name) {
    uploadForm.name = file.name.replace(/\.[^/.]+$/, '')
  }
}

// 确认上传
const confirmUpload = () => {
  // 根据上传方式验证
  if (uploadMode.value === 'local' && !uploadForm.file) {
    ElMessage.warning('请选择文件')
    return
  }
  if (uploadMode.value === 'cloud' && !uploadForm.cloudPath) {
    ElMessage.warning('请从云端选择文件')
    return
  }
  if (!uploadForm.name) {
    ElMessage.warning('请输入文件名称')
    return
  }

  const now = new Date()
  const uploadTime = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`

  const newPdf: FileItem = {
    id: `pdf-${Date.now()}`,
    name: uploadForm.name + '.pdf',
    size: uploadForm.file ? uploadForm.file.size : 0,
    uploadTime,
    description: uploadForm.description
  }
  if (uploadForm.cloudPath) {
    newPdf.cloudPath = uploadForm.cloudPath
  }
  pdfList.value.push(newPdf)
  ElMessage.success(`PDF文件 "${newPdf.name}" 上传成功`)
  
  uploadDialogVisible.value = false
  uploadForm.name = ''
  uploadForm.description = ''
  uploadForm.file = null
  uploadForm.cloudPath = ''
}

// 确认编辑
const confirmEdit = () => {
  const index = pdfList.value.findIndex(item => item.id === editForm.id)
  if (index > -1) {
    pdfList.value[index].description = editForm.description
    ElMessage.success('修改成功')
  }
  editDialogVisible.value = false
}

// ============ 文件夹相关函数 ============

// 显示新建文件夹对话框
const showCreateFolderDialog = () => {
  createFolderForm.name = ''
  createFolderForm.description = ''
  createFolderDialogVisible.value = true
}

// 确认创建文件夹
const confirmCreateFolder = () => {
  if (!createFolderForm.name.trim()) {
    ElMessage.warning('请输入文件夹名称')
    return
  }

  const now = new Date()
  const createTime = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`

  const newFolder: FolderItem = {
    id: `folder-pdf-${Date.now()}`,
    name: createFolderForm.name.trim(),
    fileCount: 0,
    createTime,
    description: createFolderForm.description
  }

  pdfFolders.value.push(newFolder)
  saveDataToLocalStorage() // 保存到 localStorage

  createFolderDialogVisible.value = false
  ElMessage.success(`文件夹"${newFolder.name}"创建成功`)
}

// 查看文件夹
const viewFolder = (row: FolderItem, type: 'pdf' | 'audio') => {
  // 跳转到文件夹详情页面
  router.push({
    path: '/admin/folder-detail',
    query: {
      folderId: row.id,
      type: type
    }
  })
}

// 编辑文件夹（重命名）
const editFolder = (row: FolderItem) => {
  currentEditingFolder.value = row
  renameFolderForm.name = row.name
  renameFolderDialogVisible.value = true
}

// 确认重命名文件夹
const confirmRenameFolder = () => {
  if (!renameFolderForm.name.trim()) {
    ElMessage.warning('请输入文件夹名称')
    return
  }

  if (!currentEditingFolder.value) return

  const targetFolders = activeTab.value === 'audio' ? audioFolders : pdfFolders
  const index = targetFolders.value.findIndex(f => f.id === currentEditingFolder.value!.id)
  if (index > -1) {
    targetFolders.value[index].name = renameFolderForm.name.trim()
    saveDataToLocalStorage() // 保存到 localStorage
    ElMessage.success('重命名成功')
  }

  renameFolderDialogVisible.value = false
  currentEditingFolder.value = null
}

// 删除文件夹
const deleteFolder = (row: FolderItem) => {
  ElMessageBox.confirm(
    `确定要删除文件夹"${row.name}"吗？\n注意：文件夹内的文件不会被删除。`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    pdfFolders.value = pdfFolders.value.filter(f => f.id !== row.id)
    saveDataToLocalStorage() // 保存到 localStorage
    ElMessage.success('删除成功')
  }).catch(() => {})
}

// PDF选择变化
const handlePdfSelectionChange = (selection: FileItem[]) => {
  selectedPdfFiles.value = selection
}

// 显示移动文件对话框
const showMoveFileDialog = () => {
  if (selectedPdfFiles.value.length === 0) {
    ElMessage.warning('请先选择要移动的文件')
    return
  }
  
  targetFolderId.value = ''
  moveFileDialogVisible.value = true
}

// 确认移动文件
const confirmMoveFiles = () => {
  if (!targetFolderId.value) {
    ElMessage.warning('请选择目标文件夹')
    return
  }
  
  const selectedFiles = selectedPdfFiles.value
  
  // 更新文件的文件夹ID
  selectedFiles.forEach(file => {
    const index = pdfList.value.findIndex(f => f.id === file.id)
    if (index > -1) {
      pdfList.value[index].folderId = targetFolderId.value
    }
  })
  
  // 更新文件夹文件数量
  const folderIndex = pdfFolders.value.findIndex(f => f.id === targetFolderId.value)
  if (folderIndex > -1) {
    pdfFolders.value[folderIndex].fileCount += selectedFiles.length
  }
  
  // 清除选中状态
  selectedPdfFiles.value = []
  pdfTableRef.value?.clearSelection()
  
  moveFileDialogVisible.value = false
  ElMessage.success(`已将 ${selectedFiles.length} 个文件移动到文件夹`)
}

// 编辑PDF课件
const editPdfCourseware = (row: FileItem) => {
  router.push({
    path: '/admin/courseware-generate',
    query: { pdfId: row.id }
  })
}

// 查看PDF - 跳转到PDF阅读器页面
const viewPdf = (row: FileItem) => {
  // 跳转到PDF阅读器页面
  router.push({
    path: '/pdf-reader',
    query: {
      taskId: row.id,
      fromAdmin: 'true' // 标记从管理后台进入
    }
  })
}

// 删除PDF
const deletePdf = (row: FileItem) => {
  ElMessageBox.confirm(`确定要删除文件"${row.name}"吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    pdfList.value = pdfList.value.filter(item => item.id !== row.id)
    ElMessage.success('删除成功')
  }).catch(() => {})
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}
</script>

<style scoped>
.material-library-page {
  padding: 20px;
}

.page-title {
  margin: 0 0 20px 0;
  font-size: 24px;
  color: #303133;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.filter-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.folder-name-link {
  color: #409eff;
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
}

.folder-name-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}
</style>
