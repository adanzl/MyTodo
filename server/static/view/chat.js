import { getList, setData } from "../js/net_util.js";

const { ref, onMounted } = window.Vue;
let component = null;
async function loadTemplate() {
  const response = await fetch("./view/chat-template.html");
  return await response.text(); // 获取模板内容
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        userList: ref([]),
        loading: ref(false),
        textInput: ref(""),
        chatMessages : ref([]),
      };
      const refreshUserList = async () => {
        refData.loading.value = true;
        const data = await getList("t_user");
        // console.log("getUserList", data.data);
        Object.assign(refData.userList.value, data.data); // 浅合并
        refData.loading.value = false;
      };
      const refMethods = {
        handleUpdateUser: (item) => {
          const data = {
            id: item.id,
            score: item.score,
          };
          setData("t_user", data).then(() => {
            // console.log("update user", data);
            refreshUserList();
          });
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
