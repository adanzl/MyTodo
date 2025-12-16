import { getList } from "../js/net_util.js";

const { ref, onMounted } = window.Vue;
const _ = window._;
const dayjs = window.dayjs;
let component = null;
async function loadTemplate() {
  const response = await fetch(`./view/score-template.html?t=${Date.now()}`);
  return await response.text(); // 获取模板内容
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        PAGE_SIZE: 10,
        userList: ref([]),
        recordList: ref([
          {
            data: [],
            pageNum: 1,
            pageSize: 10,
            totalCount: 0,
            totalPage: 0,
          },
        ]),
        loading: ref(false),
        selectedUser: ref(),
      };

      const refreshUserList = async () => {
        const data = await getList("t_user");
        // console.log("getUserList", data.data);
        Object.assign(refData.userList.value, data.data); // 浅合并
        refData.userList.value.unshift({ id: 0, name: "全部" });
        refData.selectedUser.value = refData.userList.value[0];
      };
      const refreshRecordList = async (userId, pageNum, pageSize) => {
        refData.loading.value = true;
        let filter = undefined;
        if (userId && userId !== 0) {
          filter = { user_id: userId };
        }
        getList("t_score_history", filter, pageNum, pageSize)
          .then((data) => {
            const d = data.data;
            console.log(data);
            refData.recordList.value.data = [];
            refData.recordList.value.pageNum = data.pageNum;
            refData.recordList.value.pageSize = data.pageSize;
            refData.recordList.value.totalCount = data.totalCount;
            refData.recordList.value.totalPage = data.totalPage;

            _.forEach(d, (item) => {
              item.user = refMethods.getUserInfo(item.user_id);
              item.dt =  dayjs(item.dt).format("YYYY-MM-DD HH:mm:ss");
              refData.recordList.value.data.push(item);
            });
          })
          .finally(() => {
            refData.loading.value = false;
          });
      };
      const refMethods = {
        getUserInfo: (id) => {
          return _.find(refData.userList.value, (item) => item.id == id);
        },
        onUserChange: async (item) => {
          console.log("onUserChange", item);
          await refreshRecordList(item.id, 1, refData.PAGE_SIZE);
        },
        handlePageChange: (pageNum, pageSize) => {
          refreshRecordList(refData.selectedUser.value.id, pageNum, pageSize);
        },
      };
      onMounted(async () => {
        await refreshUserList();
        await refreshRecordList(0, 1, refData.PAGE_SIZE);
        // console.log("Score组件已挂载");
      });
      return {
        ...refData,
        ...refMethods,
      };
    },
    template,
  };
  return component;
}
export default createComponent();
