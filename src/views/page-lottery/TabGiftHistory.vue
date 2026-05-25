<template>
  <ion-segment-content id="tabGiftHistory">
    <div class="h-full">
      <ion-item>
        <ion-select
          class="min-w-0 flex-1"
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
          class="min-w-0 flex-1"
          label="奖池"
          justify="start"
          :value="selectedPoolId"
          @ionChange="onPoolChange">
          <ion-select-option :value="0">全部</ion-select-option>
          <ion-select-option
            v-for="pool in poolList"
            :key="pool.id"
            :value="pool.id">
            {{ pool.name }}
          </ion-select-option>
        </ion-select>
        <div class="ml-2 flex shrink-0 items-center justify-end">
          <ion-checkbox
            label-placement="end"
            justify="start"
            :checked="onlyWish"
            class="text-sm"
            @ionChange="onWishChange">
            仅心愿单
          </ion-checkbox>
        </div>
      </ion-item>

      <ion-content :scrollY="true" :style="{ height: 'calc(100% - 56px)' }">
        <ion-refresher slot="fixed" @ionRefresh="onRefresh">
          <ion-refresher-content />
        </ion-refresher>

        <ion-item
          v-for="item in recordList.data"
          :key="item.id"
          button
          @click="onGiftClick(item)">
          <div class="flex min-w-0 flex-1 flex-col py-1">
            <div class="flex items-start justify-between gap-0">
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between">
                  <span class="truncate text-[15px] font-medium text-slate-800">
                    {{'[' + (item.gift_id || 0) + ']' + (item.gift_name || `礼物 #${item.gift_id}`) }}
                  </span>
                </div>
                <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 px-1">
                  <span>{{ getUserName(item.user_id) }}</span>
                  <span>类型：{{ getRecordTypeLabel(item.gift_pool_id) }}</span>
                  <span>分类：{{ getCateLabel(item.gift_cate_id) }}</span>
                  <span>奖池：{{ getPoolLabel(item.gift_pool_id) }}</span>
                </div>
                <div class="flex mt-1 text-xs text-gray-500 gap-2 px-1">
                  <span>心愿：{{ item.wish === 1 ? "是" : "否" }}</span>
                  <span>{{ formatDate(item.dt) }}</span>
                </div>
                <div
                  v-if="item.msg"
                  class="mt-1 line-clamp-2 text-xs text-gray-500  px-1">
                  {{ item.msg }}
                </div>
              </div>

            </div>
          </div>
          <div slot="end" class="flex h-full flex-col items-center py-1" @click.stop>
            <ion-badge :color="item.status === 2 ? 'success' : 'medium'" class="p-1 text-[10px]">
              {{ item.status === 2 ? "已核销" : "待核销" }}
            </ion-badge>
            <div class="flex-1 flex items-center justify-center">
              <ion-button
                size="small"
                fill="outline"
                :color="item.status === 2 ? 'medium' : 'success'"
                :disabled="!isAdmin"
                @click="onToggleVerify(item)">
                {{ item.status === 2 ? "取消" : "核销" }}
              </ion-button>
            </div>
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
  </ion-segment-content>
</template>

<script setup lang="ts">
import { getGiftCategoryList, getGiftData, getGiftPoolList } from "@/api/api-lottery";
import { getList, setData } from "@/api/data";
import {
  IonBadge,
  IonButton,
  IonCheckbox,
  IonContent,
  IonInfiniteScroll,
  IonInfiniteScrollContent,
  IonItem,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
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

interface RecordTypeOption {
  id: number;
  name?: string;
}

const REFRESH_EVENT = "lottery-gift-history-refresh";
const PAGE_SIZE = 20;

const props = defineProps<{
  userList: Array<{ id: number; name?: string }>;
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
const selectedPoolId = ref(0);
const onlyWish = ref(false);
const poolList = ref<RecordTypeOption[]>([]);
const poolMap = ref(new Map<number, string>());
const cateMap = ref(new Map<number, string>());
let refreshSequence = 0;

const filteredUserList = computed(() =>
  props.userList.filter((item) => item.id !== 0)
);

const hasMore = computed(() => {
  const { pageNum, totalPage, data, totalCount } = recordList.value;
  if (loading.value) return false;
  if (totalCount > 0 && data.length < totalCount) return true;
  return pageNum < totalPage;
});

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
  if (selectedPoolId.value > 0) {
    filter.gift_pool_id = selectedPoolId.value;
  }
  if (onlyWish.value) {
    filter.wish = 1;
  }
  return Object.keys(filter).length > 0 ? filter : undefined;
}

async function fetchPoolOptions() {
  const data = await getGiftPoolList({ pageNum: 1, pageSize: 500 });
  const list = data.data ?? [];
  const options = list.map((item) => ({
    id: Number(item.id),
    name: item.name,
  }));
  return {
    list: options,
    map: new Map(options.map((item) => [item.id, item.name || `奖池${item.id}`])),
  };
}

async function fetchCateLookup() {
  const data = await getGiftCategoryList({ pageNum: 1, pageSize: 500 });
  const list = data.data ?? [];
  return new Map(
    list
      .filter((item) => item.id != null)
      .map((item) => [Number(item.id), item.name || String(item.id)])
  );
}

async function fetchRecordPage(
  filter: Record<string, unknown> | undefined,
  pageNum: number,
  pageSize: number
) {
  const data = await getList<GiftHistoryItem>("t_gift_history", filter, pageNum, pageSize);
  const rows = data.data ?? [];
  const mappedRows: GiftHistoryItem[] = rows.map((item) => ({
    ...item,
    id: Number(item.id ?? 0),
    user_id: Number(item.user_id ?? 0),
    gift_id: Number(item.gift_id ?? 0),
    gift_name: item.gift_name ?? "",
    gift_pool_id: item.gift_pool_id,
  }));

  return {
    data: mappedRows,
    pageNum: Number(data.pageNum) || pageNum,
    pageSize: Number(data.pageSize) || pageSize,
    totalCount: Number(data.totalCount) || 0,
    totalPage: Number(data.totalPage) || 0,
  };
}

async function refreshRecordList(pageNum: number, append: boolean = false, reloadMeta: boolean = false) {
  const requestId = ++refreshSequence;
  const filter = buildFilter();
  const pageSize = recordList.value.pageSize;
  loading.value = true;
  try {
    const [recordResult, poolResult, cateResult] = await Promise.allSettled([
      fetchRecordPage(filter, pageNum, pageSize),
      reloadMeta ? fetchPoolOptions() : Promise.resolve(null),
      reloadMeta ? fetchCateLookup() : Promise.resolve(null),
    ]);

    if (requestId !== refreshSequence) {
      return;
    }

    if (poolResult.status === "fulfilled" && poolResult.value) {
      poolList.value = poolResult.value.list;
      poolMap.value = poolResult.value.map;
    } else if (poolResult.status === "rejected") {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(poolResult.reason));
    }

    if (cateResult.status === "fulfilled" && cateResult.value) {
      cateMap.value = cateResult.value;
    } else if (cateResult.status === "rejected") {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(cateResult.reason));
    }

    if (recordResult.status !== "fulfilled") {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(recordResult.reason));
      return;
    }

    const nextPage = recordResult.value;

    if (!append) {
      recordList.value = {
        data: nextPage.data,
        pageNum: nextPage.pageNum,
        pageSize: nextPage.pageSize,
        totalCount: nextPage.totalCount,
        totalPage: nextPage.totalPage,
      };
      return;
    }

    recordList.value.data.push(...nextPage.data);
    recordList.value.pageNum = nextPage.pageNum;
    recordList.value.pageSize = nextPage.pageSize;
    recordList.value.totalCount = nextPage.totalCount;
    recordList.value.totalPage = nextPage.totalPage;
  } finally {
    if (requestId === refreshSequence) {
      loading.value = false;
    }
  }
}

function handleFilterRefresh() {
  void refreshRecordList(1);
}

function handleManualRefresh() {
  void refreshRecordList(1, false, true);
}

function onRefresh(event: CustomEvent) {
  refreshRecordList(1, false, true).finally(() => {
    event.target && (event.target as HTMLIonRefresherElement).complete();
  });
}

function onUserChange(event: CustomEvent) {
  selectedUserId.value = Number(event.detail.value || 0);
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
  void refreshRecordList(recordList.value.pageNum + 1, true).finally(() => {
    event.target && (event.target as HTMLIonInfiniteScrollElement).complete();
  });
}

async function onToggleVerify(item: GiftHistoryItem) {
  if (!isAdmin.value) {
    return;
  }
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
  if (!item.gift_id) {
    EventBus.$emit(C_EVENT.TOAST, item.msg || "未找到礼物信息");
    return;
  }

  const loading = await loadingController.create({ message: "加载中..." });
  await loading.present();
  try {
    const gift = await getGiftData(item.gift_id);
    EventBus.$emit(C_EVENT.REWARD, {
      value: gift.name || item.gift_name || `礼物 #${item.gift_id}`,
      img: gift.image || "",
      rewardType: "gift" as const,
      msg: item.msg || "",
    });
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    await loading.dismiss();
  }
}

function handleExternalRefresh() {
  handleManualRefresh();
}

onMounted(async () => {
  window.addEventListener(REFRESH_EVENT, handleExternalRefresh);
  await refreshRecordList(1, false, true);
});

onBeforeUnmount(() => {
  window.removeEventListener(REFRESH_EVENT, handleExternalRefresh);
});
</script>
