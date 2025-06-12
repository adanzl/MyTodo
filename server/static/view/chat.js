import { getList, setData, getRdsData, getRdsList } from "../js/net_util.js";

const { ref, onMounted } = window.Vue;
const _ = window._;
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
        chatMessages: ref([]),
        chatSetting: ref({
          open: false,
          ttsSpeed: 1.1,
          ttsRole: "",
          aiConversationId: "",
          chatRoomId: "v_chat_room_001",
        }),
      };
      const refreshUserList = async () => {
        refData.loading.value = true;
        const data = await getList("t_user");
        // console.log("getUserList", data.data);
        Object.assign(refData.userList.value, data.data); // 浅合并
        refData.loading.value = false;
      };
      const getChatSetting = async () => {
        const data = await getRdsData("chatSetting", window.curUser.id);
        console.log("getChatSetting", data);
        if (data) {
          refData.chatSetting.value = data.data;
        }
      };
      const refreshChatList = async () => {
        refData.loading.value = true;
        const data = await getRdsList("chat:" + refData.chatSetting.value.chatRoomId, 1, 20);
        console.log("getUserList", data.data);
        Object.assign(refData.userList.value, data.data); // 浅合并
        _.forEach(data.data, (item) => {
          const d = JSON.parse(item);
          refData.chatMessages.value.unshift({
            id: "_",
            content: d.content,
            role: d.user_id,
            ts: d.ts,
            type: d.type,
          });
        });
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
        getUserInfo: (userId) => {
          return refData.userList.value.find((u) => u.id === userId);
        },
        onSendBtnClick: () => {
          if (!refData.textInput.value) {
            return;
          }
          console.log("onSendBtnClick", refData.textInput.value);
          refData.textInput.value = "";
          
        },
      };
      onMounted(async () => {
        await refreshUserList();
        await getChatSetting();
        refreshChatList();
        // console.log("Home组件已挂载");
      });
      return {
        ...refData,
        ...refMethods,
      };
    },
    data() {
      return { window };
    },
    template,
  };
  return component;
}
export default createComponent();
