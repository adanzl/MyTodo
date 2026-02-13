<template>
  <div class="">
    <div class="flex flex-wrap items-end gap-2 mb-2">
      <div class="flex items-center">
        <el-text class="w-24">普通抽奖费用</el-text>
        <el-input v-model="lotterySettingData.fee" class="!w-32 ml-2" type="number" />
      </div>
      <div class="flex items-center">
        <el-text class="w-28">心愿单阈值</el-text>
        <el-input v-model.number="lotterySettingData.wish_count_threshold" class="!w-32 ml-2" type="number" placeholder="5" />
        <el-text class="ml-2 text-gray-500 text-sm">进度达到后下一抽仅从心愿单池抽取并清零</el-text>
      </div>
      <el-button type="primary" @click="handleUpdateFee">更新配置</el-button>
    </div>
    <el-divider />
    <div class="flex items-center">
      <el-radio-group size="large" v-model="selectedCateId" class="" @change="onCateChange">
        <el-radio-button v-for="item in lotteryCatList" :key="item.id" :value="item.id">
          {{ item.name }}
        </el-radio-button>
      </el-radio-group>
      <el-button type="primary" class="ml-1" @click="modifyCateModel = true">
        <el-icon>
          <Edit />
        </el-icon>
      </el-button>
      <div class="flex-1 flex items-center justify-end">
        <el-button type="primary" class="" @click="onAddGiftClk">添加奖品</el-button>
      </div>
    </div>
    <el-table :data="giftList.data" v-loading="loading">
      <!-- 图片 -->
      <el-table-column width="130" label="Image">
        <template #default="{ row }">
          <div class="h-24 flex">
            <template v-if="row.edited">
              <!-- 图片 -->
              <div class="flex items-center w-24">
                <template v-if="!row.img">
                  <el-upload class="flex items-center justify-center bg-white w-full h-full" action="#"
                    list-type="picture-card" :limit="1" :auto-upload="false" :show-file-list="false"
                    :on-change="(file: UploadFile) => handleImageChange(file, row)">
                    <el-icon>
                      <Plus />
                    </el-icon>
                  </el-upload>
                </template>
                <template v-else>
                  <div class="relative z-50 w-full h-full">
                    <el-image class="w-24 cursor-pointer !z-[99]" :src="getPicDisplayUrl(row.img)"
                      :preview-src-list="[getPicDisplayUrl(row.img)]" :preview-teleported="true" fit="contain" />
                    <el-upload class="absolute bottom-0 right-0 !z-[100]" action="#" :show-file-list="false"
                      :auto-upload="false" :on-change="(file: UploadFile) => handleImageChange(file, row)">
                      <el-button size="small" type="primary" circle>
                        <el-icon>
                          <Edit />
                        </el-icon>
                      </el-button>
                    </el-upload>
                  </div>
                </template>
              </div>
            </template>
            <template v-else>
              <div class="relative w-24">
                <el-image class="w-24 cursor-pointer !z-[9999]" :src="getPicDisplayUrl(row.img)"
                  :preview-src-list="[getPicDisplayUrl(row.img)]" :preview-teleported="true" fit="contain" />
              </div>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="Info" width="200">
        <template #default="{ row }">
          <div class="flex flex-col">
            <el-descriptions :column="1" size="small" border label-width="50">
              <el-descriptions-item label="ID" width="100">
                <el-input v-model="row.id" size="small" disabled></el-input>
              </el-descriptions-item>
              <el-descriptions-item label="名称">
                <el-input v-model="row.name" size="small" :disabled="!row.edited" />
              </el-descriptions-item>
              <el-descriptions-item label="Cost">
                <el-input v-model="row.cost" size="small" :disabled="!row.edited" />
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="Exchange" width="100" align="center">
        <template #default="{ row }">
          <el-checkbox v-model="row.exchange" :true-value="1" :false-value="0" :disabled="!row.edited" />
        </template>
      </el-table-column>
      <el-table-column label="Stock" width="100" align="center">
        <template #default="{ row }">
          <el-input v-model.number="row.stock" size="small" :disabled="!row.edited" type="number" />
        </template>
      </el-table-column>
      <el-table-column label="Category" width="180">
        <template #default="{ row }">
          <div class="flex items-center">
            <el-select :disabled="!row.edited" v-model="row.cate_id" @change="handleGiftCatChange($event, row)">
              <el-option v-for="item in lotteryCatList" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <div class="flex items-center pl-2">
            <el-checkbox v-model="row.enable" size="large" :disabled="!row.edited" />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="心愿单" width="80" align="center">
        <template #default="{ row }">
          <el-checkbox v-model="row.wish" :true-value="true" :false-value="false" :disabled="!row.edited" />
        </template>
      </el-table-column>
      <el-table-column label="Operations">
        <template #default="{ row }">
          <div class="flex flex-col gap-2 [&_.el-button+_.el-button]:!ml-0">
            <el-button v-if="row.id !== -1" class="w-16" size="small" type="danger" @click="handleGiftDel(row)">
              Delete
            </el-button>
            <el-button v-if="row.edited" class="w-16" size="small"
              @click="handleGiftCancel(row, giftList.data.indexOf(row))">
              Cancel
            </el-button>
            <el-button v-else size="small" class="w-16" @click="handleCateEdit(row)">
              Edit
            </el-button>
            <el-button v-if="row.edited" class="w-16" size="small" type="primary" @click="handleGiftSave(row)">
              Save
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination layout="prev, pager, next" :total="giftList.totalCount" :page-size="PAGE_SIZE"
      :current-page="giftList.pageNum" class="mt-2" background
      @current-change="(page: number) => handlePageChange(page, PAGE_SIZE)" />
  </div>
  <el-dialog v-model="modifyCateModel" title="类别管理" width="800" destroy-on-close>
    <el-table :data="lotteryCatPopList">
      <el-table-column property="id" label="ID" width="50" />
      <el-table-column property="name" label="Name" width="100">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.name" size="small"
                @blur="handleCateBlur(row, 'name', lotteryCatPopList.indexOf(row))" />
            </template>
            <template v-else>
              <span> {{ row.name }} </span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column property="cost" label="Cost" width="200">
        <template #default="{ row }">
          <div class="flex items-center">
            <template v-if="row.edited">
              <el-input v-model="row.cost" size="small" clearable
                @blur="handleCateBlur(row, 'cost', lotteryCatPopList.indexOf(row))" />
            </template>
            <template v-else>
              <span> {{ row.cost }} </span>
            </template>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="OP">
        <template #default="{ row }">
          <el-button v-if="row.edited" class="w-16" size="small" type="primary"
            @click="handleCateSave(row, lotteryCatPopList.indexOf(row))">
            Save
          </el-button>
          <el-button v-if="row.edited" class="w-16" size="small"
            @click="handleCateCancel(row, lotteryCatPopList.indexOf(row))">
            Cancel
          </el-button>
          <el-button v-else size="small" class="w-16" @click="handleCateEdit(row)">
            Edit
          </el-button>
          <el-button v-if="row.id !== -1" class="w-16" size="small" type="danger" @click="handleCateDelete(row)">
            Delete
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import type { UploadFile } from "element-plus";
import { Edit, Plus } from "@element-plus/icons-vue";
import { getList, getData, setData, delData } from "@/api/common";
import { getRdsData, setRdsData } from "@/api/rds";
import { uploadPic, getPicDisplayUrl } from "@/api/pic";
import * as _ from "lodash-es";

interface Gift {
  id: number;
  name: string;
  img: string;
  cate_id: number;
  cost: number;
  enable: boolean;
  exchange: number;
  stock: number;
  wish: boolean;
  edited?: boolean;
}

interface GiftApiData {
  id: number;
  name: string;
  image: string;
  cate_id: number;
  cost: number;
  enable: number;
  exchange?: number;
  stock?: number;
  wish?: number;
}

interface GiftCategory {
  id: number;
  name: string;
  cost?: number;
  edited?: boolean;
}

const PAGE_SIZE = 10;
const selectedCateId = ref<number>(0);
const selectedCate = computed(() => {
  return (
    lotteryCatList.value.find(item => item.id === selectedCateId.value) || lotteryCatList.value[0]
  );
});
const giftList = ref<{
  data: Gift[];
  pageNum: number;
  pageSize: number;
  totalCount: number;
  totalPage: number;
}>({
  data: [],
  pageNum: 1,
  pageSize: 20,
  totalCount: 0,
  totalPage: 0,
});
const lotteryCatList = ref<GiftCategory[]>([]);
const loading = ref(false);
const lotterySettingData = ref({ fee: 10, wish_count_threshold: 5 });
const modifyCateModel = ref(false);
const lotteryCatPopList = ref<GiftCategory[]>([]);

const refreshCateList = async () => {
  try {
    const response = await getList<GiftCategory>("t_gift_category");
    if (response && response.data) {
      const d = response.data.data || [];
      lotteryCatList.value = [...d];
      lotteryCatList.value.unshift({ id: 0, name: "全部" });
      if (selectedCateId.value === 0 && lotteryCatList.value.length > 0) {
        selectedCateId.value = lotteryCatList.value[0].id;
      }

      lotteryCatPopList.value = [];
      lotteryCatPopList.value.push({ id: -1, name: "", edited: true });
      _.forEach(d, (item: GiftCategory) => {
        lotteryCatPopList.value.push({
          id: item.id,
          name: item.name,
          cost: item.cost,
          edited: false,
        });
      });
    }
  } catch (err) {
    console.error(err);
    ElMessage.error(JSON.stringify(err));
  }
};

const refreshGiftList = async (cateId: number, pageNum: number, pageSize: number) => {
  loading.value = true;
  try {
    let filter: Record<string, number> | undefined = undefined;
    if (cateId && cateId !== 0) {
      filter = { cate_id: cateId };
    }
    const response = await getList<GiftApiData>("t_gift", filter, pageNum, pageSize);
    if (response && response.data) {
      const d = response.data.data || [];
      giftList.value.data = [];
      giftList.value.pageNum = response.data.pageNum ?? pageNum;
      giftList.value.pageSize = response.data.pageSize ?? pageSize;
      giftList.value.totalCount = response.data.totalCount ?? 0;
      giftList.value.totalPage =
        response.data.totalPage ??
        Math.ceil((response.data.totalCount ?? 0) / (response.data.pageSize ?? pageSize));

      _.forEach(d, item => {
        giftList.value.data.push({
          id: item.id,
          name: item.name,
          img: item.image,
          cate_id: item.cate_id,
          cost: item.cost,
          enable: item.enable === 1,
          exchange: item.exchange ?? 0,
          stock: item.stock ?? 0,
          wish: (item.wish ?? 0) === 1,
          edited: false,
        });
      });
    }
  } catch (err) {
    console.error(err);
    ElMessage.error(JSON.stringify(err));
  } finally {
    loading.value = false;
  }
};

const handleUpdateFee = async () => {
  try {
    const payload = {
      fee: lotterySettingData.value.fee,
      wish_count_threshold: lotterySettingData.value.wish_count_threshold ?? 5,
    };
    await setRdsData("lottery", 2, JSON.stringify(payload));
    ElMessage.success("已更新：普通抽奖费用、心愿单阈值");
  } catch (error) {
    console.error("更新配置失败:", error);
    ElMessage.error("更新配置失败");
  }
};

const onCateChange = () => {
  const cate = selectedCate.value;
  if (cate) {
    refreshGiftList(cate.id, 1, PAGE_SIZE);
  }
};

const onAddGiftClk = () => {
  giftList.value.data.unshift({
    id: -1,
    name: "",
    img: "",
    cate_id: selectedCate.value.id,
    cost: 0,
    enable: false,
    exchange: 0,
    stock: 0,
    wish: false,
    edited: true,
  });
};

const handleGiftCatChange = (event: number, item: Gift) => {
  item.cate_id = event;
};

const handleGiftDel = async (item: Gift) => {
  try {
    item.edited = false;
    await delData("t_gift", item.id);
    await refreshGiftList(selectedCate.value.id, giftList.value.pageNum, giftList.value.pageSize);
  } catch (error) {
    console.error("删除奖品失败:", error);
    ElMessage.error("删除奖品失败");
  }
};

const handleGiftCancel = async (item: Gift, idx: number) => {
  if (item.id === -1) {
    giftList.value.data.splice(idx, 1);
  } else {
    item.edited = false;
    try {
      const data = await getData<GiftApiData>("t_gift", item.id);
      Object.assign(item, {
        id: data.id,
        name: data.name,
        img: data.image,
        cate_id: data.cate_id,
        cost: data.cost,
        enable: data.enable === 1,
        exchange: data.exchange ?? 0,
        stock: data.stock ?? 0,
        wish: (data.wish ?? 0) === 1,
      });
    } catch (error) {
      console.error("获取奖品数据失败:", error);
    }
  }
};

const handleGiftSave = async (item: Gift) => {
  try {
    const data = {
      id: item.id,
      name: item.name,
      image: item.img,
      cate_id: item.cate_id,
      enable: item.enable ? 1 : 0,
      cost: item.cost,
      exchange: item.exchange ?? 0,
      stock: item.stock ?? 0,
      wish: item.wish ? 1 : 0,
    };
    await setData("t_gift", data);
    await refreshGiftList(selectedCate.value.id, giftList.value.pageNum, giftList.value.pageSize);
  } catch (error) {
    console.error("保存奖品失败:", error);
    ElMessage.error("保存奖品失败");
  }
};

const handleImageChange = async (file: UploadFile, row: Gift) => {
  if (file && file.raw) {
    try {
      const resp = await uploadPic(file.raw);
      if (resp.code === 0 && resp.data?.filename) {
        row.img = resp.data.filename;
      } else {
        ElMessage.error(resp.msg || "图片上传失败");
      }
    } catch (error) {
      console.error("图片上传失败:", error);
      ElMessage.error("图片上传失败");
    }
  }
};

const handlePageChange = (pageNum: number, pageSize: number) => {
  refreshGiftList(selectedCate.value.id, pageNum, pageSize);
};

const handleCateBlur = (item: GiftCategory, key: string, _idx: number) => {
  console.log("handleCateBlur", item, key);
};

const handleCateSave = async (item: GiftCategory, _idx: number) => {
  try {
    const data = {
      id: item.id,
      name: item.name,
      cost: item.cost,
    };
    await setData("t_gift_category", data);
    await refreshCateList();
  } catch (error) {
    console.error("保存类别失败:", error);
    ElMessage.error("保存类别失败");
  }
};

const handleCateDelete = async (item: GiftCategory) => {
  try {
    await delData("t_gift_category", item.id);
    await refreshCateList();
  } catch (error) {
    console.error("删除类别失败:", error);
    ElMessage.error("删除类别失败");
  }
};

const handleCateEdit = (item: GiftCategory) => {
  item.edited = true;
};

const handleCateCancel = (item: GiftCategory, _idx: number) => {
  if (item.id === -1) {
    item.name = "";
    item.cost = 0;
  } else {
    item.edited = false;
  }
};

const getLotterySetting = async () => {
  try {
    const data = await getRdsData("lottery", 2);
    if (data) {
      const parsed = JSON.parse(data as string);
      lotterySettingData.value = {
        fee: parsed.fee ?? 10,
        wish_count_threshold: parsed.wish_count_threshold ?? 5,
      };
    }
  } catch (error) {
    console.error("获取抽奖设置失败:", error);
  }
};

onMounted(async () => {
  await refreshCateList();
  await refreshGiftList(0, 1, PAGE_SIZE);
  await getLotterySetting();
});
</script>

<style scoped></style>
