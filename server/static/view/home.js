import { getList, setData, addScore } from "../js/net_util.js";

const { ref, onMounted } = window.Vue;
let component = null;
async function loadTemplate() {
  const response = await fetch("./view/home-template.html");
  return await response.text(); // 获取模板内容
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        userList: ref([]),
        dialogForm: ref({
          visible: false,
          data: null,
          value: 0,
        }),
      };
      const refreshUserList = async () => {
        const data = await getList("t_user");
        // console.log("getUserList", data.data);
        Object.assign(refData.userList.value, data.data); // 浅合并
      };
      const refMethods = {
        handleUpdateUser: (item) => {
          const data = {
            id: item.id,
            score: item.score,
          };
          setData("t_user", data).then(() => {
            console.log("update user", data);
            refreshUserList();
          });
        },
        onAddScoreBtnClick: (item) => {
          refData.dialogForm.value.visible = true;
          refData.dialogForm.value.data = item;
        },
        handleAddScore: () => {
          addScore(
            refData.dialogForm.value.data.id,
            "pcAdmin",
            refData.dialogForm.value.value,
            "管理后台变更"
          ).then(() => {
            refreshUserList();
          });
        },
        handleDialogClose: () => {
          refData.dialogForm.value.visible = false;
          refData.dialogForm.value.value = 0;
        },
      };
      onMounted(async () => {
        await refreshUserList();
        console.log("Home组件已挂载");
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
