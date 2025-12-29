<template>
  <div class="max-w-250 h-full bg-blue-100 flex flex-col">
    <h1 class="text-center">Chat length [{{ chatMessages.length }}]</h1>
    <div class="h-[300px]">
      <van-pull-refresh
        v-model="loading"
        @refresh="onRefresh"
        class="h-full"
        :scroll-target="() => $refs.chatContent"
      >
        <div ref="chatContent" class="h-full overflow-y-auto">
          <div v-for="(msg, idx) in chatMessages" :key="idx" class="p-1.5 w-full message-item">
            <!-- 我的消息 -->
            <div v-if="msg.role == currentUserId" class="flex">
              <div
                class="max-w-[70%] min-w-[40px] bg-green-500 text-white p-2 ml-auto rounded-lg shadow-md relative"
              >
                {{ msg.content }}
              </div>
              <el-avatar :src="getUserInfo(msg.role)?.icon" class="w-12 h-12 ml-1"> </el-avatar>
              <div
                v-if="!msg.audioSrc"
                class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
                @click="btnAudioClk(msg)"
              >
                <i-mdi-stop-circle-outline class="w-6 h-6" v-if="msg.playing" />
                <i-ion-volume-medium-outline class="w-6 h-6" v-else />
              </div>
            </div>
            <!-- 对方消息 -->
            <div v-else class="flex">
              <el-avatar :src="getUserInfo(msg.role)?.icon" class="w-12 h-12 ml-1"> </el-avatar>
              <div
                class="max-w-[70%] min-w-[40px] bg-pink-200 rounded-lg ml-2 p-2 shadow-md mr-auto relative"
              >
                {{ msg.content }}
              </div>
            </div>
          </div>
        </div>
        <div
          v-if="showBackTop"
          class="fixed bottom-20 right-4 z-50 w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center cursor-pointer shadow-lg"
          @click="scrollToTop"
        >
          <el-icon :size="20" color="white"><ArrowUp /></el-icon>
        </div>
      </van-pull-refresh>
    </div>
    <div class="flex bg-green-500">
      <el-input
        v-model="textInput"
        class="w-full h-17 ml-2 mt-2"
        type="textarea"
        placeholder="Please input"
      ></el-input>
      <el-button class="!w-16 !h-13 mx-2 mt-2" type="primary" @click="onSendBtnClick">
        Send
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, inject, onUnmounted, computed, type Ref } from "vue";
import { ElMessage } from "element-plus";
import { ArrowUp } from "@element-plus/icons-vue";
import { io, type Socket } from "socket.io-client";
import * as _ from "lodash-es";
import { getRdsData, getRdsList } from "@/api/rds";
import { getApiUrl } from "@/api/config";
import { useUserStore } from "@/stores/user";
import type { User } from "@/types/user";

interface CurUser {
  bLogin: boolean;
  id: number | null;
  name: string | null;
  ico: string | null;
}

interface ChatMessage {
  id: string;
  content: string;
  role: number;
  ts?: string;
  type: string;
  audioSrc?: string;
  playing?: boolean;
}

interface WindowWithCurUser extends Window {
  curUser?: CurUser;
}

const CHAT_PAGE_SIZE = 3;
const curUser = inject<Ref<CurUser>>(
  "curUser",
  ref({ bLogin: false, id: null, name: null, ico: null })
);

// 使用 Pinia Store
const userStore = useUserStore();
const userList = computed(() => userStore.userList as User[]);

// 获取当前用户 ID
const currentUserId = computed(() => {
  return (window as WindowWithCurUser).curUser?.id || curUser.value?.id;
});

const loading = ref(false);
const textInput = ref("");
const chatContent = ref<HTMLElement | null>(null);
const chatMessages = ref<ChatMessage[]>([]);
const showBackTop = ref(false);
const chatSetting = ref({
  open: false,
  ttsSpeed: 1.1,
  ttsRole: "",
  aiConversationId: "",
  chatRoomId: "v_chat_room_001",
});
const socketRef = ref<Socket | null>(null);

const wsUrl = getApiUrl().replace("api", "");

function initSocket() {
  if (socketRef.value) {
    socketRef.value.disconnect();
  }

  socketRef.value = io(wsUrl, {
    transports: ["websocket"],
    timeout: 20000,
    autoConnect: false,
    forceNew: true,
  });

  socketRef.value.on("connect", () => {
    const chatConfig = {
      key: "123456",
      ttsAuto: false,
      chatRoomId: chatSetting.value.chatRoomId,
      user: (window as WindowWithCurUser).curUser?.name || curUser.value?.name || "",
    };
    console.log("Connected to the server. Send handshake...", chatConfig);
    socketRef.value?.emit("handshake", chatConfig);
  });

  socketRef.value.on("handshakeResponse", data => {
    console.log("handshakeResponse:", data);
  });

  socketRef.value.on("connect_error", error => {
    console.error("Connection error:", error);
  });

  socketRef.value.on("disconnect", () => console.log("Disconnected from the server."));
  socketRef.value.on("error", error => console.error("msg error:", error));
  socketRef.value.on("close", () => console.log("WebSocket connection closed."));
  socketRef.value.on("endChat", data => {
    console.log("endChat", data);
  });
  socketRef.value.on("msgChat", data => {
    if (data.chat_type === "chat_room") {
      chatMessages.value.push({
        id: "_",
        content: data.content,
        role: data.user_id,
        ts: data.ts,
        type: data.type,
      });
    } else {
      ElMessage.error(JSON.stringify(data));
    }
  });

  // 手动连接
  socketRef.value.connect();
}

const refreshUserList = async () => {
  // 使用 Pinia Store 刷新用户列表
  await userStore.refreshUserList();
};

const getChatSetting = async () => {
  try {
    const userId = currentUserId.value;
    if (userId === null || userId === undefined) {
      return;
    }
    const data = await getRdsData("chatSetting", userId);
    if (data) {
      const settingData = typeof data === "string" ? JSON.parse(data) : data;
      chatSetting.value = (settingData as { data?: typeof chatSetting.value }).data || settingData;
    }
  } catch (error) {
    console.error("获取聊天设置失败:", error);
  }
};

const scrollChatToBottom = () => {
  nextTick(() => {
    setTimeout(() => {
      const el = chatContent.value;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    }, 10);
  });
};

const getChatMessages = async (startId: number, pageSize: number, bScroll: boolean) => {
  loading.value = true;
  try {
    const response = await getRdsList("chat:" + chatSetting.value.chatRoomId, startId, pageSize);
    const data = (response as { data?: string[] }).data || [];
    _.forEachRight(data, (item: string) => {
      const d = JSON.parse(item) as { content: string; user_id: number; ts?: string; type: string };
      chatMessages.value.unshift({
        id: "_",
        content: d.content,
        role: d.user_id,
        ts: d.ts,
        type: d.type,
      });
    });
  } catch (error) {
    console.error("获取聊天消息失败:", error);
  } finally {
    loading.value = false;
  }
  if (bScroll) {
    scrollChatToBottom();
  }
};

const getUserInfo = (userId: number) => {
  return userList.value.find(u => u.id === userId);
};

const onSendBtnClick = () => {
  if (!textInput.value) {
    return;
  }
  const userId = (window as WindowWithCurUser).curUser?.id || curUser.value?.id;
  chatMessages.value.push({
    id: "_",
    content: textInput.value,
    role: userId || 0,
    type: "text",
  });
  const message = JSON.stringify({
    type: "text",
    content: textInput.value,
    chatType: "chat_room",
    roomId: chatSetting.value.chatRoomId,
    userId: userId,
  });
  socketRef.value?.emit("message", message);
  console.log("send message:", message);
  textInput.value = "";
  scrollChatToBottom();
};

const onRefresh = async () => {
  const firstId = chatMessages.value.length + 1;
  await getChatMessages(-firstId, CHAT_PAGE_SIZE, false);
};

const btnAudioClk = (msg: ChatMessage) => {
  // TODO: 音频播放功能
  console.log("btnAudioClk", msg);
};

const scrollToTop = () => {
  if (chatContent.value) {
    chatContent.value.scrollTo({ top: 0, behavior: "smooth" });
  }
};

const handleScroll = () => {
  if (chatContent.value) {
    showBackTop.value = chatContent.value.scrollTop > 100;
  }
};

onMounted(async () => {
  await refreshUserList();
  await getChatSetting();
  await getChatMessages(-1, CHAT_PAGE_SIZE, true);
  initSocket();

  // 监听滚动事件
  nextTick(() => {
    if (chatContent.value) {
      chatContent.value.addEventListener("scroll", handleScroll);
    }
  });
});

onUnmounted(() => {
  if (socketRef.value) {
    socketRef.value.disconnect();
  }
  if (chatContent.value) {
    chatContent.value.removeEventListener("scroll", handleScroll);
  }
});
</script>

<style scoped>
.message-item {
  min-height: 60px;
}
</style>
