import { getList, setData, addScore } from "../js/net_util.js";

const { ref, onMounted } = window.Vue;
let component = null;
async function loadTemplate() {
  const response = await fetch("./view/device-template.html");
  return await response.text(); // 获取模板内容
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        dialogForm: ref({
          visible: false,
          data: null,
          value: 0,
        }),
        loading: ref(false),
      };
      const refreshUserList = async () => {
        refData.loading.value = true;
        // console.log("getUserList", data.data);
        refData.loading.value = false;
      };
      const refMethods = {
        handleUpdateUser: (item) => {},

        handleDialogClose: () => {
          refData.dialogForm.value.visible = false;
          refData.dialogForm.value.value = 0;
        },
      };
      onMounted(async () => {
        await refreshUserList();
        // console.log("Home组件已挂载");
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
