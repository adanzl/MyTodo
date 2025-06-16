import { getList, setData, getRdsData, getRdsList, getApiUrl } from "../js/net_util.js";

const { ref, onMounted } = window.Vue;
const _ = window._;
const { ElMessage } = window.ElementPlus;
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
      // const wsUrl = getApiUrl().replace("api", "");
      const wsUrl = "http://localhost:8000"; // 使用 /api 前缀
      console.log(getApiUrl());
      const socketRef = ref();
      function initSocket() {
        if (socketRef.value) {
          socketRef.value.disconnect();
        }

        socketRef.value = window.io(wsUrl, {
          transports: ["websocket"],
          path: "/api/socket.io/",
          timeout: 20000,
          autoConnect: false,
          forceNew: true,
        });

        socketRef.value.on("connect", () => {
          const chatConfig = {
            key: "123456",
            ttsAuto: false,
            chatRoomId: refData.chatSetting.value.chatRoomId,
            user: window.curUser.name,
          };
          console.log("Connected to the server. Sending handshake...", chatConfig);
          // socketRef.value.emit("handshake", chatConfig);
        });

        socketRef.value.on("handshakeResponse", (data) => {
          console.log("handshakeResponse:", data);
        });

        socketRef.value.on("connect_error", (error) => {
          console.error("Connection error:", error);
        });

        socketRef.value.on("disconnect", () => console.log("Disconnected from the server."));
        socketRef.value.on("error", (error) => console.error("msg error:", error));
        socketRef.value.on("close", () => console.log("WebSocket connection closed."));
        socketRef.value.on("msgChat", (data) => {
          if (data.chat_type === "chat_room") {
            refData.chatMessages.value.unshift({
              id: "_",
              content: data.content,
              role: data.user_id,
              ts: data.ts,
              type: data.type,
            });
          } else {
            ElMessage.error(JSON.stringify(data));
          }
          // aiChatContent.value.$el.scrollToBottom(200);
        });

        // 手动连接
        socketRef.value.connect();
      }

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
        const data = await getRdsList("chat:" + refData.chatSetting.value.chatRoomId, -1, 20);
        _.forEachRight(data.data, (item) => {
          const d = JSON.parse(item);
          // console.log("d", d);
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
          // console.log("getUserInfo", userId);
          // console.log(refData.userList.value);
          return refData.userList.value.find((u) => u.id === userId);
        },
        onSendBtnClick: (event) => {
          if (event) {
            event.preventDefault();
            event.stopPropagation();
          }
          if (!refData.textInput.value) {
            return;
          }
          // const message = JSON.stringify({
          //   type: "text",
          //   content: refData.textInput.value,
          //   chatType: "chat_room",
          //   roomId: refData.chatSetting.value.chatRoomId,
          //   userId: window.curUser.id,
          // });
          // socketRef.value.emit("message", message);
          // console.log("send message:", message);
          const chatConfig = {
            key: "123456",
            ttsAuto: false,
            chatRoomId: refData.chatSetting.value.chatRoomId,
            user: window.curUser.name,
          };
          socketRef.value.emit("handshake", chatConfig, (response) => {
            console.log(response);
          });
          refData.textInput.value = "";
        },
      };
      onMounted(async () => {
        await refreshUserList();
        await getChatSetting();
        refreshChatList();
        initSocket();
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
