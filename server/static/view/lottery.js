import { getData, getList, setData, delData, getRdsData } from "../js/net_util.js";
import { compressImageToBase64 } from "../js/image_util.js";
const _ = window._;
const { ref, onMounted } = window.Vue;
const { ElMessage } = window.ElementPlus;
let component = null;
async function loadTemplate() {
  const response = await fetch("./view/lottery-template.html");
  return await response.text(); // 获取模板内容
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        PAGE_SIZE: 10,
        selectedCate: ref(),
        giftList: ref({
          data: [],
          pageNum: 1,
          pageSize: 10,
          totalCount: 0,
          totalPage: 0,
        }),
        lotteryCatList: ref([]),
        loading: ref(false),
        lotterySetting: ref({
          
        }),
      };

      const refCatePop = {
        modifyCateModel: ref(false),
        lotteryCatPopList: ref([]),
      };

      const refreshCateList = () => {
        getList("t_gift_category")
          .then((data) => {
            const d = data.data;
            // console.log(d);
            refData.lotteryCatList.value = [...d];
            refData.lotteryCatList.value.unshift({ id: 0, name: "全部" });
            if (refData.selectedCate.value == null) {
              refData.selectedCate.value = refData.lotteryCatList.value[0];
            }

            refCatePop.lotteryCatPopList.value = [];
            refCatePop.lotteryCatPopList.value.push({ id: -1, name: "", edited: true });
            _.forEach(d, (item) => {
              refCatePop.lotteryCatPopList.value.push({
                id: item.id,
                name: item.name,
                cost: item.cost,
                edited: false,
              });
            });
          })
          .catch((err) => {
            console.error(err);
            ElMessage.error(JSON.stringify(err));
          });
      };
      const refreshGiftList = (cateId, pageNum, pageSize) => {
        refData.loading.value = true;
        let filter = undefined;
        if (cateId && cateId !== 0) {
          filter = { cate_id: cateId };
        }
        getList("t_gift", filter, pageNum, pageSize)
          .then((data) => {
            const d = data.data;
            // console.log(data);
            refData.giftList.value.data = [];
            refData.giftList.value.pageNum = data.pageNum;
            refData.giftList.value.pageSize = data.pageSize;
            refData.giftList.value.totalCount = data.totalCount;
            refData.giftList.value.totalPage = data.totalPage;

            _.forEach(d, (item) => {
              refData.giftList.value.data.push({
                id: item.id,
                name: item.name,
                img: item.image,
                cate_id: item.cate_id,
                cost: item.cost,
                edited: false,
              });
            });
          })
          .catch((err) => {
            console.error(err);
            ElMessage.error(JSON.stringify(err));
          })
          .finally(() => (refData.loading.value = false));
      };
      const handleEdit = (index, row) => {
        console.log(index, row);
      };
      const handleDelete = (index, row) => {
        console.log(index, row);
      };
      const onCateChange = (item) => {
        refData.selectedCate.value = item;
        refreshGiftList(item.id);
      };
      const giftFunc = {
        onAddGiftClk: () => {
          refData.giftList.value.data.unshift({
            id: -1,
            name: "",
            img: "",
            cate: refData.selectedCate.value.id,
            cost: 0,
            edited: true,
          });
        },
        handleGiftCatChange: (event, item) => {
          item.cate_id = event;
        },
        handleGiftDel: (item) => {
          item.edited = false;
          delData("t_gift", item.id).then(() => {
            refreshGiftList();
          });
        },
        handleGiftCancel: (item, idx) => {
          if (item.id === -1) {
            refData.giftList.value.data.splice(idx, 1);
          } else {
            item.edited = false;
            getData("t_gift", item.id, "*").then((data) => {
              // console.log(data);
              Object.assign(item, data);
              // item.name = data.name;
              // item.img = data.image;
              // item.cate_id = data.cate_id;
              // item.cost = data.cost;
            });
          }
        },
        handleGiftSave: (item) => {
          const data = {
            id: item.id,
            name: item.name,
            image: item.img,
            cate_id: item.cate_id,
            cost: item.cost,
          };
          // console.log("handleGiftSave", item, data, idx);
          setData("t_gift", data).then(() => {
            refreshGiftList();
          });
        },
        handleImageChange: (file, row) => {
          if (file) {
            compressImageToBase64(file.raw, 0.5).then((base64) => {
              console.log("压缩后的base64", base64.length);
              row.img = base64;
            });
          }
        },
        handlePageChange: (pageNum, pageSize) => {
          refreshGiftList(refData.selectedCate.value.id, pageNum, pageSize);
        },
      };
      const catePopFunc = {
        handleCateBlur: (item, key, idx) => {
          console.log("handleCateBlur", item, key, idx);
        },
        handleCateSave: (item, key, idx) => {
          console.log("handleCateSave", item, key, idx);
          const data = {
            id: item.id,
            name: item.name,
            cost: item.cost,
          };
          setData("t_gift_category", data).then(() => {
            refreshCateList();
          });
        },
        handleCateDelete: (item, key, idx) => {
          console.log("handleCateDelete", item, key, idx);
        },
        handleCateEdit: (item) => {
          item.edited = true;
        },
        handleCateCancel: (item) => {
          if (item.id === -1) {
            item.name = "";
            item.cost = 0;
          } else {
            item.edited = false;
          }
        },
      };
      const getLotterySetting = async () => {
        getRdsData("lotterySetting").then((data) => {
          // console.log("getLotterySetting", data);
          if (data) {
            refData.lotterySetting = data;
          }
        });
      };
      onMounted(() => {
        // console.log("Lottery组件已挂载");
        refreshCateList();
        refreshGiftList(0, 1, refData.PAGE_SIZE);
        getLotterySetting();
      });
      return {
        ...refData,
        ...refCatePop,
        refreshData: refreshCateList,
        handleEdit,
        handleDelete,
        onCateChange,
        ...giftFunc,
        ...catePopFunc,
      };
    },
    data() {
      return {
        message: "欢迎来到Lottery",
      };
    },
    methods: {},
    template,
  };
  return component;
}

export default createComponent();
