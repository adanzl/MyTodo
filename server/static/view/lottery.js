const Lottery = {
  data() {
    return {
      message: "欢迎来到Lottery",
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
    </div>
  `,
  async mounted() {
    const response = await fetch("/static/view/home.html");
    const template = await response.text();
    this.$options.template = template;
    this.$forceUpdate();
    console.log("Lottery组件已挂载");
  },
};

export default Lottery;
