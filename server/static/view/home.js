import { getUserList } from "../js/net_util.js";

const { ref } = window.Vue;
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
      };
      return {
        ...refData,
      };
    },
    data() {
      return {
        message: "欢迎来到首页",
        count: 0,
      };
    },
    methods: {
      increment() {
        this.count++;
      },
    },
    template,
    async mounted() {
      const data = await getUserList();
      console.log("getUserList", data.data);
      Object.assign(this.userList, data.data); // 浅合并
      console.log("Home组件已挂载");
    },
  };
  return component;
}
export default createComponent();
