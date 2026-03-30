<template>
    <ion-modal ref="modal" aria-hidden="false" id="lottery-pool" :is-open="isOpen" @didPresent="onModalPresent"
        @willDismiss="onModalWillDismiss">
        <ion-header>
            <ion-toolbar>
                <ion-buttons slot="start">
                    <ion-button fill="clear" @click="cancel()"> <ion-icon :icon="closeOutline" /></ion-button>
                </ion-buttons>
                <ion-title>奖池管理</ion-title>
                <ion-buttons slot="end">
                    <ion-button @click="addPool">添加奖池</ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>
        <ion-content class="ion-padding">
            <!-- 奖池列表 -->
            <ion-list>
                <ion-item v-for="pool in poolList" :key="pool.id" button detail class="py-2 rounded-xl"
                    @click="editPool(pool)">
                    <div class="py-2">
                        <div class="flex items-center mb-1">
                            <p class="flex items-center w-10 shrink-0"> ID: </p>
                            <p class="flex items-center w-9 shrink-0">{{ pool.id }} </p>
                            <p class="flex items-center flex-1">{{ pool.name }}</p>
                        </div>
                        <div class="flex text-xs mt-1">
                            <p class="w-10 shrink-0"> 积分： </p>
                            <p class="w-9 shrink-0">{{ pool.cost }} </p>
                            <p class="w-15 shrink-0"> 中奖数： </p>
                            <p class="w-8">{{ pool.count }} - {{ pool.count_mx }} </p>
                        </div>
                        <div class="flex text-xs mt-2">
                            <p class="w-9 shrink-0 "> 类别： </p>
                            <!-- 有类别时 -->
                            <div class="flex gap-1">
                                <template v-if="pool.cateNames && pool.cateNames.length > 0">
                                    <div v-for="(name, idx) in pool.cateNames" :key="idx"
                                        class="text-xs px-1 py-1 rounded-sm bg-blue-100 text-blue-800">
                                        {{ name }}
                                    </div>
                                </template>
                                <!-- 无类别时 -->
                                <div v-else color="medium"
                                    class="text-xs px-1 py-1 rounded-sm bg-gray-100 text-gray-800">
                                    无
                                </div>
                            </div>
                        </div>
                    </div>
                    <div slot="end" class="flex flex-col gap-1" @click.stop>
                        <ion-button size="small" fill="outline" @click="editPool(pool)">编辑</ion-button>
                        <ion-button size="small" fill="outline" color="danger" @click="deletePool(pool)">
                            删除
                        </ion-button>
                    </div>
                </ion-item>
                <ion-item v-if="poolList.length === 0">
                    <ion-label class="text-gray-500">暂无奖池，请添加</ion-label>
                </ion-item>
            </ion-list>

            <!-- 编辑/添加奖池对话框 -->
            <ion-modal ref="editModal" id="lotteryPoolEditModal" mode="ios" aria-hidden="false" class="backdrop"
                :is-open="isEditDialogOpen" @didPresent="onEditDialogPresent" @willDismiss="onEditDialogWillDismiss">
                <ion-item>
                    <ion-title>{{ editingPool ? '编辑奖池' : '添加奖池' }}</ion-title>
                </ion-item>
                <ion-content class="ion-padding">
                    <div class="flex flex-col gap-1">
                        <ion-item lines="full" class="rounded-md">
                            <div class="w-12 shrink-0">ID</div>
                            <div class="flex-1 text-gray-500 ">{{ editForm.id }}</div>
                        </ion-item>
                        <ion-item lines="full" class="rounded-md">
                            <div class="w-12 shrink-0 ">名称</div>
                            <ion-input v-model="editForm.name" type="text" placeholder="请输入奖池名称" :clear-input="true" />
                        </ion-item>

                        <div class="grid grid-cols-3 gap-2">
                            <ion-item lines="full">
                                <ion-input v-model.number="editForm.cost" type="number" placeholder="积分"
                                    inputmode="numeric" label="积分" label-placement="stacked" />
                            </ion-item>

                            <ion-item lines="full">
                                <ion-input v-model.number="editForm.count" type="number" placeholder="数量"
                                    inputmode="numeric" label="中奖数量" label-placement="stacked" />
                            </ion-item>

                            <ion-item lines="full">
                                <ion-input v-model.number="editForm.count_mx" type="number" placeholder="最大数量"
                                    inputmode="numeric" label="最大数量" label-placement="stacked" />
                            </ion-item>
                        </div>

                        <ion-item lines="none" class="rounded-md h-40! overflow-y-auto">
                            <div class="w-full py-2 ">
                                <div class="text-sm font-medium text-gray-700 mb-2">
                                    类别列表 <span class="text-xs text-primary">(已选 {{ selectedCateCount }})</span>
                                </div>
                                <div class="flex flex-wrap gap-2">
                                    <ion-chip v-for="cate in lotteryCatList" :key="cate.id"
                                        :color="isSelectedCate(cate.id) ? 'primary' : 'medium'" :outline="false"
                                        class="rounded-md px-2" @click="toggleCate(cate.id)">
                                        <ion-icon :icon="checkmarkCircle"
                                            :class="isSelectedCate(cate.id) ? 'text-blue-500' : 'text-gray-300'"
                                            class="w-4 h-4 mr-1">
                                        </ion-icon>
                                        {{ cate.name }}
                                    </ion-chip>
                                </div>
                                <!-- 隐藏的 textarea，用于存储实际的 cate_list 值 -->
                                <textarea v-model="editForm.cate_list" class="hidden" readonly>
                    </textarea>
                            </div>
                        </ion-item>
                    </div>
                </ion-content>
                <ion-footer class="flex!">
                    <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancelEdit()">取消</ion-button>
                    <ion-button class="flex-1 text-orange-400" fill="clear" @click="savePool()">确定</ion-button>
                </ion-footer>
            </ion-modal>
        </ion-content>
    </ion-modal>
</template>

<script lang="ts" setup>
import { setLotteryPool, delLotteryPool } from "@/api/api-lottery";
import { getList } from "@/api/data";
import { getNetworkErrorMessage } from "@/utils/net-util";
import EventBus, { C_EVENT } from "@/types/event-bus";
import { ref, computed } from "vue";
import { alertController, loadingController } from "@ionic/vue";
import { checkmarkCircle, closeOutline } from "ionicons/icons";

defineProps<{
    isOpen: boolean;
}>();

const emit = defineEmits<{
    (e: "willDismiss", event: any): void;
    (e: "refresh"): void;
}>();

const modal = ref();
const poolList = ref<any[]>([]);
const bModify = ref(false);
const categoryMap = ref<Map<number, any>>(new Map());
const lotteryCatList = ref<any[]>([]);

// 编辑对话框相关
const isEditDialogOpen = ref(false);
const editingPool = ref<any>(null);
const editForm = ref({
    id: null as number | null,
    name: '',
    cost: 0,
    count: 1,
    count_mx: 0 as number | undefined,
    cate_list: '',
});

async function onModalPresent() {
    bModify.value = false;
    const loading = await loadingController.create({
        message: "Loading...",
    });
    loading.present();

    try {
        // 并行获取奖池数据和类别数据
        const [poolsData, categoriesData] = await Promise.all([
            getList("t_gift_pool"),
            getList("t_gift_category"),
        ]);

        // 构建类别映射表（key 为 category id）
        const map = new Map<number, any>();
        lotteryCatList.value = categoriesData?.data ?? [];
        (categoriesData?.data ?? []).forEach((cate: any) => {
            map.set(cate.id, cate);
        });
        categoryMap.value = map;

        // 组合数据：将类别信息注入到奖池数据中
        poolList.value = (poolsData?.data ?? []).map((pool: any) => {
            // 处理 cate_list：用逗号分割的 ID 列表，转换为类别名称数组
            let cateNames: string[] = [];
            if (pool.cate_list) {
                const ids = String(pool.cate_list).split(',').map((id: string) => Number(id.trim()));
                cateNames = ids
                    .map((id: number) => map.get(id)?.name)
                    .filter((name: string | undefined) => name !== undefined);
            }

            return {
                ...pool,
                cateNames, // 类别名称数组
            };
        });
    } catch (err: any) {
        EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    } finally {
        loading.dismiss();
    }
}

const onModalWillDismiss = (event: any) => {
    emit("willDismiss", event);
};

// 编辑对话框相关函数
function onEditDialogPresent() {
    // 对话框打开时的初始化
}

function onEditDialogWillDismiss() {
    // 对话框关闭前的清理
    isEditDialogOpen.value = false;
    editingPool.value = null;
}

function cancelEdit() {
    isEditDialogOpen.value = false;
    editingPool.value = null;
}

// 判断类别是否已选中
function isSelectedCate(cateId: number): boolean {
    if (!editForm.value.cate_list) return false;
    const selectedIds = String(editForm.value.cate_list)
        .split(',')
        .map((id: string) => Number(id.trim()))
        .filter((id: number) => !isNaN(id));
    return selectedIds.includes(cateId);
}

// 计算已选择的类别数量
const selectedCateCount = computed(() => {
    if (!editForm.value.cate_list) return 0;
    const selectedIds = String(editForm.value.cate_list)
        .split(',')
        .map((id: string) => Number(id.trim()))
        .filter((id: number) => !isNaN(id));
    return selectedIds.length;
});

// 切换类别选中状态
function toggleCate(cateId: number) {
    const currentIds = editForm.value.cate_list
        ? String(editForm.value.cate_list)
            .split(',')
            .map((id: string) => Number(id.trim()))
            .filter((id: number) => !isNaN(id))
        : [];

    const index = currentIds.indexOf(cateId);
    if (index > -1) {
        // 取消选中
        currentIds.splice(index, 1);
    } else {
        // 添加选中
        currentIds.push(cateId);
    }

    editForm.value.cate_list = currentIds.join(',');
}

async function savePool() {
    // 验证表单
    const name = editForm.value.name?.trim();
    if (!name) {
        EventBus.$emit(C_EVENT.TOAST, "请输入奖池名称");
        return;
    }

    // 立即显示加载菊花
    const loading = await loadingController.create({
        message: editingPool.value ? "更新中..." : "添加中...",
    });
    await loading.present();

    try {
        await setLotteryPool({
            id: editForm.value.id ?? undefined,
            name,
            cost: Number(editForm.value.cost) || 0,
            count: Number(editForm.value.count) || 1,
            count_mx: editForm.value.count_mx !== undefined ? Number(editForm.value.count_mx) || 0 : undefined,
            cate_list: editForm.value.cate_list?.trim() ?? '',
        });

        EventBus.$emit(C_EVENT.TOAST, editingPool.value ? "更新成功" : "添加成功");
        bModify.value = true;
        isEditDialogOpen.value = false;
        editingPool.value = null;

        // 刷新列表
        onModalPresent();
        emit("refresh");
    } catch (err: any) {
        EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    } finally {
        loading.dismiss();
    }
}

function addPool() {
    // 重置表单
    editForm.value = {
        id: null,
        name: '',
        cost: 0,
        count: 1,
        count_mx: undefined,
        cate_list: '',
    };
    editingPool.value = null;
    isEditDialogOpen.value = true;
}

function editPool(pool: any) {
    // 填充表单数据
    editForm.value = {
        id: pool.id,
        name: pool.name,
        cost: pool.cost,
        count: pool.count,
        count_mx: pool.count_mx !== undefined ? pool.count_mx : undefined,
        cate_list: pool.cate_list || '',
    };
    editingPool.value = pool;
    isEditDialogOpen.value = true;
}

const cancel = async () => {
    if (bModify.value) {
        const alert = await alertController.create({
            header: "Confirm",
            message: "确认放弃修改",
            buttons: [
                {
                    text: "OK",
                    handler: () => {
                        modal.value.$el!.dismiss({}, "cancel");
                    },
                },
                "Cancel",
            ],
        });
        await alert.present();
    } else {
        modal.value.$el!.dismiss({}, "cancel");
    }
};

async function deletePool(pool: any) {
    const alert = await alertController.create({
        header: "确认删除",
        message: `确定删除奖池「${pool.name}」吗？`,
        buttons: [
            { text: "取消", role: "cancel" },
            {
                text: "确定",
                role: "confirm",
                handler: async () => {
                    try {
                        await delLotteryPool(pool.id);
                        EventBus.$emit(C_EVENT.TOAST, "删除成功");
                        bModify.value = true;
                        poolList.value = poolList.value.filter((x) => x.id !== pool.id);
                        emit("refresh");
                    } catch (err: any) {
                        EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
                    }
                },
            },
        ],
    });
    await alert.present();
}
</script>

<style scoped>
ion-modal#lottery-pool::part(content) {
    max-width: 600px;
}

ion-modal#lottery-pool {
    --height: 100%;
}

/* 编辑弹窗样式 */
ion-modal#lotteryPoolEditModal {
    --height: 500px;
    --width: 95%;
}
</style>
