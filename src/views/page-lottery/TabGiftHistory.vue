<template>
  <ion-segment-content id="tabGiftHistory">
    <div class="flex h-full flex-col">
      <div class="grid grid-cols-2 gap-2 px-3 pb-2 pt-2">
        <ion-select
          label="用户"
          justify="start"
          :value="selectedUserId"
          @ionChange="onUserChange">
          <ion-select-option :value="0">全部</ion-select-option>
          <ion-select-option
            v-for="item in filteredUserList"
            :key="item.id"
            :value="item.id">
            {{ item.name }}
          </ion-select-option>
        </ion-select>
        <ion-select
          label="类型"
          justify="start"
          :value="selectedRecordType"
          @ionChange="onRecordTypeChange">
          <ion-select-option value="all">全部</ion-select-option>
          <ion-select-option value="lottery">抽奖</ion-select-option>
          <ion-select-option value="exchange">兑换</ion-select-option>
        </ion-select>
        <ion-select
          label="奖池"
          justify="start"
          :value="selectedPoolId"
          :disabled="selectedRecordType !== 'lottery'"
          @ionChange="onPoolChange">
          <ion-select-option :value="0">全部奖池</ion-select-option>
          <ion-select-option
            v-for="pool in poolList"
            :key="pool.id"
            :value="pool.id">
            {{ pool.name }}
          </ion-select-option>
        </ion-select>
        <ion-item lines="none" class="rounded-md">
          <ion-checkbox
            label-placement="end"
            justify="start"
            :checked="onlyWish"
            @ionChange="onWishChange">
            仅心愿单
          </ion-checkbox>
        </ion-item>
      </div>

      <div class="flex items-center justify-between px-4 pb-2 text-sm">
        <div class="flex items-center text-gray-600">
          <Icon icon="mdi:star" class="mr-1 h-5 w-5 text-red-500" />
          <span>当前积分 {{ userScore }}</span>
        </div>
        <ion-button size="small" fill="clear" @click="handleManualRefresh">
          刷新
        </ion-button>
      </div>

      <ion-content :scrollY="true">
        <ion-refresher slot="fixed" @ionRefresh="onRefresh">
          <ion-refresher-content />
        </ion-refresher>

        <ion-item
          v-for="item in recordList.data"
          :key="item.id"
          button
          @click="onGiftClick(item)">
          <div class="flex min-w-0 flex-1 flex-col py-1">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0 flex-1">
                <div class="truncate text-[15px] font-medium text-slate-800">
                  {{ item.gift_name || `礼物 #${item.gift_id}` }}
                </div>
                <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
                  <span>用户：{{ getUserName(item.user_id) }}</span>
                  <span>类型：{{ getRecordTypeLabel(item.gift_pool_id) }}</span>
                  <span>分类：{{ getCateLabel(item.gift_cate_id) }}</span>
                  <span>奖池：{{ getPoolLabel(item.gift_pool_id) }}</span>
                  <span>心愿：{{ item.wish === 1 ? "是" : "否" }}</span>
                </div>
                <div class="mt-1 text-xs text-gray-500">
                  {{ formatDate(item.dt) }}
                </div>
                <div
                  v-if="item.msg"
                  class="mt-1 line-clamp-2 text-xs text-gray-500">
                  {{ item.msg }}
                </div>
              </div>
              <ion-badge :color="item.status === 2 ? 'success' : 'medium'">
                {{ item.status === 2 ? "已核销" : "待核销" }}
              </ion-badge>
            </div>
          </div>
          <div slot="end" class="pl-2" @click.stop>
            <ion-button
              size="small"
              fill="outline"
              :color="item.status === 2 ? 'medium' : 'success'"
              :disabled="!isAdmin"
              @click="onToggleVerify(item)">
              {{ item.status === 2 ? "取消" : "核销" }}
            </ion-button>
          </div>
        </ion-item>

        <ion-item v-if="!loading && recordList.data.length === 0" lines="none">
          <div class="w-full py-10 text-center text-sm text-gray-400">
            暂无礼物记录
          </div>
        </ion-item>

        <ion-infinite-scroll
          threshold="150px"
          :disabled="!hasMore"
          @ionInfinite="onLoadMore">
          <ion-infinite-scroll-content
            loading-spinner="crescent"
            loading-text="加载更多..." />
        </ion-infinite-scroll>
      </ion-content>
    </div>

    <ion-modal :is-open="giftDetailOpen" @willDismiss="closeGiftDetail">
      <ion-header>
        <ion-toolbar>
          <ion-title>礼物详情</ion-title>
          <ion-buttons slot="end">
            <ion-button @click="closeGiftDetail">关闭</ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      <ion-content class="ion-padding">
        <div
          v-if="giftDetail"
          class="flex min-h-full flex-col items-center justify-center gap-4 py-4">
          <img
            :src="giftDetailImageUrl"
            alt="gift"
            class="h-48 w-48 rounded-xl bg-gray-100 object-contain" />
          <div class="text-lg font-semibold text-slate-800">
            {{ giftDetail.name || "-" }}
          </div>
          <div class="text-sm text-gray-500">
            价值：{{ giftDetail.cost ?? "-" }}
          </div>
        </div>
      </ion-content>
    </ion-modal>
  </ion-segment-content>
</template>

<script setup lang="ts">
import { getGiftCategoryList, getGiftData, getGiftPoolList } from "@/api/api-lottery";
import { getPicDisplayUrl } from "@/api/api-pic";
import { getList, setData } from "@/api/data";
import { Icon } from "@iconify/vue";
import {
  IonBadge,
  IonButton,
  IonButtons,
  IonCheckbox,
  IonContent,
  IonHeader,
  IonInfiniteScroll,
  IonInfiniteScrollContent,
  IonItem,
  IonModal,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
  IonTitle,
  IonToolbar,
  loadingController,
} from "@ionic/vue";
import dayjs from "dayjs";
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue";
import EventBus, { C_EVENT } from "@/types/event-bus";
import { getNetworkErrorMessage } from "@/utils/net-util";

interface GiftHistoryItem {
  id: number;
  user_id: number;
  gift_id: number;
  gift_name?: string;
  gift_pool_id?: number;
  gift_cate_id?: number;
  wish?: number;
  status?: number;
  msg?: string;
  dt?: string;
  [key: string]: unknown;
}

interface GiftHistoryApiData extends Omit<GiftHistoryItem, "gift_id" | "gift_name" | "gift_pool_id"> {
  gift_id?: number;
  gitf_id?: number;
  gift_name?: string;
  gitf_name?: string;
  gift_pool_id?: number;
  gitf_pool_id?: number;
}

interface GiftDetailItem {
  id?: number;
  name?: string;
  image?: string;
  cost?: number;
}

interface RecordTypeOption {
  id: number;
  name?: string;
}

const REFRESH_EVENT = "lottery-gift-history-refresh";
const PAGE_SIZE = 20;

const props = defineProps<{
  userList: Array<{ id: number; name?: string }>;
  userScore: number;
}>();

const globalVar: any = inject("globalVar");
const isAdmin = computed(() => globalVar?.user?.admin === 1);

const recordList = ref({
  data: [] as GiftHistoryItem[],
  pageNum: 1,
  pageSize: PAGE_SIZE,
  totalCount: 0,
  totalPage: 0,
});
const loading = ref(false);
const selectedUserId = ref(0);
const selectedRecordType = ref<"all" | "lottery" | "exchange">("all");
const selectedPoolId = ref(0);
const onlyWish = ref(false);
const poolList = ref<RecordTypeOption[]>([]);
const poolMap = ref(new Map<number, string>());
const cateMap = ref(new Map<number, string>());
const giftDetailOpen = ref(false);
const giftDetail = ref<GiftDetailItem | null>(null);

const filteredUserList = computed(() =>
  props.userList.filter((item) => item.id !== 0)
);

const hasMore = computed(() => {
  const { pageNum, totalPage, data, totalCount } = recordList.value;
  if (loading.value) return false;
  if (totalCount > 0 && data.length < totalCount) return true;
  return pageNum < totalPage;
});

const giftDetailImageUrl = computed(() =>
  getPicDisplayUrl(giftDetail.value?.image || "")
);

function formatDate(value?: string) {
  if (!value) return "-";
  return dayjs(value).format("YYYY-MM-DD HH:mm:ss");
}

function getUserName(userId: number) {
  return props.userList.find((item) => item.id === userId)?.name ?? String(userId);
}

function isExchange(poolId?: number) {
  return poolId === -1;
}

function getRecordTypeLabel(poolId?: number) {
  return isExchange(poolId) ? "兑换" : "抽奖";
}

function getPoolLabel(poolId?: number) {
  if (isExchange(poolId)) return "兑换";
  if (poolId == null) return "-";
  return poolMap.value.get(poolId) ?? `奖池${poolId}`;
}

function getCateLabel(cateId?: number) {
  if (cateId == null) return "-";
  return cateMap.value.get(cateId) ?? String(cateId);
}

function buildFilter(): Record<string, unknown> | undefined {
  const filter: Record<string, unknown> = {};
  if (selectedUserId.value > 0) {
    filter.user_id = selectedUserId.value;
  }
  if (selectedRecordType.value === "exchange") {
    filter.gitf_pool_id = -1;
  } else if (selectedRecordType.value === "lottery") {
    filter.gitf_pool_id =
      selectedPoolId.value > 0 ? selectedPoolId.value : { ">": -1 };
  }
  if (onlyWish.value) {
    filter.wish = 1;
  }
  return Object.keys(filter).length > 0 ? filter : undefined;
}

async function loadPoolMap() {
  try {
    const data = await getGiftPoolList({ pageNum: 1, pageSize: 500 });
    const list = data.data ?? [];
    poolList.value = list.map((item) => ({
      id: Number(item.id),
      name: item.name,
    }));
    poolMap.value = new Map(
      poolList.value.map((item) => [item.id, item.name || `奖池${item.id}`])
    );
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

async function loadCateMap() {
  try {
    const data = await getGiftCategoryList({ pageNum: 1, pageSize: 500 });
    const list = data.data ?? [];
    cateMap.value = new Map(
      list
        .filter((item) => item.id != null)
        .map((item) => [Number(item.id), item.name || String(item.id)])
    );
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

async function refreshRecordList(pageNum: number, append: boolean = false) {
  loading.value = true;
  try {
    const data = await getList<GiftHistoryApiData>(
      "t_gift_history",
      buildFilter(),
      pageNum,
      recordList.value.pageSize
    );

    const rows = data.data ?? [];
    const mappedRows: GiftHistoryItem[] = rows.map((item) => ({
      ...item,
      id: Number(item.id ?? 0),
      user_id: Number(item.user_id ?? 0),
      gift_id: Number(item.gift_id ?? item.gitf_id ?? 0),
      gift_name: item.gift_name ?? item.gitf_name ?? "",
      gift_pool_id: item.gift_pool_id ?? item.gitf_pool_id,
    }));

    if (!append) {
      recordList.value = {
        data: mappedRows,
        pageNum: Number(data.pageNum) || pageNum,
        pageSize: Number(data.pageSize) || recordList.value.pageSize,
        totalCount: Number(data.totalCount) || 0,
        totalPage: Number(data.totalPage) || 0,
      };
      return;
    }

    recordList.value.data.push(...mappedRows);
    recordList.value.pageNum = Number(data.pageNum) || pageNum;
    recordList.value.pageSize = Number(data.pageSize) || recordList.value.pageSize;
    recordList.value.totalCount = Number(data.totalCount) || recordList.value.totalCount;
    recordList.value.totalPage = Number(data.totalPage) || recordList.value.totalPage;
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    loading.value = false;
  }
}

function handleFilterRefresh() {
  refreshRecordList(1);
}

function handleManualRefresh() {
  loadPoolMap();
  loadCateMap();
  refreshRecordList(1);
}

function onRefresh(event: CustomEvent) {
  Promise.all([loadPoolMap(), loadCateMap(), refreshRecordList(1)]).finally(() => {
    event.target && (event.target as HTMLIonRefresherElement).complete();
  });
}

function onUserChange(event: CustomEvent) {
  selectedUserId.value = Number(event.detail.value || 0);
  handleFilterRefresh();
}

function onRecordTypeChange(event: CustomEvent) {
  selectedRecordType.value = event.detail.value;
  if (selectedRecordType.value !== "lottery") {
    selectedPoolId.value = 0;
  }
  handleFilterRefresh();
}

function onPoolChange(event: CustomEvent) {
  selectedPoolId.value = Number(event.detail.value || 0);
  handleFilterRefresh();
}

function onWishChange(event: CustomEvent) {
  onlyWish.value = Boolean(event.detail.checked);
  handleFilterRefresh();
}

function onLoadMore(event: CustomEvent) {
  if (!hasMore.value) {
    event.target && (event.target as HTMLIonInfiniteScrollElement).complete();
    return;
  }
  refreshRecordList(recordList.value.pageNum + 1, true).finally(() => {
    event.target && (event.target as HTMLIonInfiniteScrollElement).complete();
  });
}

async function onToggleVerify(item: GiftHistoryItem) {
  const nextStatus = item.status === 2 ? 1 : 2;
  try {
    await setData("t_gift_history", { id: item.id, status: nextStatus });
    item.status = nextStatus;
    EventBus.$emit(
      C_EVENT.TOAST,
      nextStatus === 2 ? "核销成功" : "已取消核销"
    );
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

async function onGiftClick(item: GiftHistoryItem) {
  if (!item.gift_id) return;

  const loadingInstance = await loadingController.create({ message: "加载中..." });
  await loadingInstance.present();
  try {
    const data = await getGiftData(item.gift_id);
    giftDetail.value = {
      id: data.id as number | undefined,
      name: data.name,
      image: data.image,
      cost: data.cost as number | undefined,
    };
    giftDetailOpen.value = true;
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    await loadingInstance.dismiss();
  }
}

function closeGiftDetail() {
  giftDetailOpen.value = false;
  giftDetail.value = null;
}

function handleExternalRefresh() {
  handleManualRefresh();
}

onMounted(async () => {
  await Promise.all([loadPoolMap(), loadCateMap()]);
  await refreshRecordList(1);
  window.addEventListener(REFRESH_EVENT, handleExternalRefresh);
});

onBeforeUnmount(() => {
  window.removeEventListener(REFRESH_EVENT, handleExternalRefresh);
});
</script>
