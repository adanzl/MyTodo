const Home = {
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
  template: `
    <div>
        <h1>{{ message }}</h1>
        <p>计数: {{ count }}</p>
        <el-button type="primary" @click="increment">增加计数</el-button>
    </div>
  `,
  async mounted() {
    const response = await fetch("/static/view/home.html");
    const template = await response.text();
    this.$options.template = template;
    this.$forceUpdate();
    console.log("Home组件已挂载");
  },
};

export default Home;
