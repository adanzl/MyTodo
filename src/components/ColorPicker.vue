<template>
  <ion-modal
    ref="modal"
    id="colorPicker"
    aria-hidden="false"
    class="bottom-modal"
    @willPresent="onWillPresent">
    <ion-header>
      <ion-toolbar>
        <ion-title>
          <h3>颜色选择</h3>
        </ion-title>
      </ion-toolbar>
    </ion-header>
    <div class="w-full h-1/4">
      <div class="flex items-center">
        <h1 class="pl-2">预览</h1>
        <div class="w-1/2 h-8 block ml-2" :style="{ background: color }"></div>
        <span class="pl-2">{{ color }}</span>
      </div>
      <canvas ref="palette" style="background: white" class="block ml-auto mr-auto"> </canvas>
      <canvas
        ref="chooser"
        style="background: white; margin-top: 20px; margin-bottom: 20px"
        class="block ml-auto mr-auto"></canvas>
    </div>
    <ion-footer class="flex">
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()"> 确定 </ion-button>
    </ion-footer>
  </ion-modal>
</template>

<style scoped></style>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
const props = defineProps({
  hexColor: {
    type: String,
    default: "#0000FF",
  },
});

const emits = defineEmits(["colorChanged", "colorTouchStart", "colorTouchEnd"]);
const modal = ref();
const color = ref("#0000FF");
const colorFromChooser = ref("#0000FF");
const paletteX = ref(0);
const paletteY = ref(0);
const chooserX = ref(0);

const palette = ref<any>();
const chooser = ref<any>();
const ctxPalette = ref<any>();

const POUCH = [
  {
    START: "mousedown",
    MOVE: "mousemove",
    STOP: "mouseup",
  },
  {
    START: "touchstart",
    MOVE: "touchmove",
    STOP: "touchend",
  },
];

const drawSelector = (ctx: any, x: number, y: number) => {
  drawPalette(colorFromChooser.value);
  ctx.beginPath();
  ctx.arc(x, y, 10 * getPixelRatio(ctx), 0, 2 * Math.PI, false);
  ctx.fillStyle = color.value;
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = "#FFFFFF";
  ctx.stroke();
};

const drawChooserSelector = (ctx: any, x: number) => {
  drawPalette(colorFromChooser.value);
  ctx.beginPath();
  ctx.arc(x, ctx.canvas.height / 2, ctx.canvas.height / 2, 0, 2 * Math.PI, false);
  ctx.fillStyle = colorFromChooser.value;
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = "#FFFFFF";
  ctx.stroke();
};

const initPalette = () => {
  const canvasPalette: any = palette.value;
  if (!canvasPalette) return;
  ctxPalette.value = canvasPalette?.getContext("2d", { willReadFrequently: true });

  const currentWidth = window.innerWidth;
  const pixelRatio = getPixelRatio(ctxPalette.value);

  const width = (currentWidth * 90) / 100;
  const height = width * 0.5;

  canvasPalette.width = width * pixelRatio;
  canvasPalette.height = height * pixelRatio;
  canvasPalette.style.width = `${width}px`;
  canvasPalette.style.height = `${height}px`;

  drawPalette(colorFromChooser.value);

  const eventChangeColor = (event: any) => {
    updateColor(event, canvasPalette, ctxPalette.value);
  };

  POUCH.forEach((pouch) => {
    canvasPalette.addEventListener(pouch.START, (event: any) => {
      emits("colorTouchStart");
      drawPalette(colorFromChooser.value);
      canvasPalette.addEventListener(pouch.MOVE, eventChangeColor);
      updateColor(event, canvasPalette, ctxPalette.value);
    });

    canvasPalette.addEventListener(pouch.STOP, (event: any) => {
      emits("colorTouchEnd");
      canvasPalette.removeEventListener(pouch.MOVE, eventChangeColor);
      updateColor(event, canvasPalette, ctxPalette.value);
      drawSelector(ctxPalette.value, paletteX.value, paletteY.value);
    });
  });
};

const drawPalette = (endColor: any) => {
  if (!ctxPalette.value) return;
  ctxPalette.value.clearRect(0, 0, ctxPalette.value.canvas.width, ctxPalette.value.canvas.height);

  let gradient = ctxPalette.value.createLinearGradient(0, 0, ctxPalette.value.canvas.width, 0);

  gradient.addColorStop(0, "#FFFFFF");
  gradient.addColorStop(1, endColor);

  ctxPalette.value.fillStyle = gradient;
  ctxPalette.value.fillRect(0, 0, ctxPalette.value.canvas.width, ctxPalette.value.canvas.height);

  gradient = ctxPalette.value.createLinearGradient(0, 0, 0, ctxPalette.value.canvas.height);
  gradient.addColorStop(0, "rgba(255, 255, 255, 1)");
  gradient.addColorStop(0.5, "rgba(255, 255, 255, 0)");
  gradient.addColorStop(0.5, "rgba(0, 0, 0, 0)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 1)");

  ctxPalette.value.fillStyle = gradient;
  ctxPalette.value.fillRect(0, 0, ctxPalette.value.canvas.width, ctxPalette.value.canvas.height);
};

const initChooser = () => {
  const canvasChooser = chooser.value;
  const ctx = canvasChooser.getContext("2d", { willReadFrequently: true });

  const currentWidth = window.innerWidth;
  const pixelRatio = getPixelRatio(ctx);

  const width = (currentWidth * 90) / 100;
  const height = width * 0.05;

  canvasChooser.width = width * pixelRatio;
  canvasChooser.height = height * pixelRatio;
  canvasChooser.style.width = `${width}px`;
  canvasChooser.style.height = `${height}px`;

  drawChooser(ctx);

  const eventChangeColorChooser = (event: any) => {
    updateColorChooser(event, canvasChooser, ctx);
    drawSelector(
      ctxPalette.value,
      ctxPalette.value.canvas.width,
      ctxPalette.value.canvas.height / 2
    );
  };

  POUCH.forEach((pouch) => {
    canvasChooser.addEventListener(pouch.START, (event: any) => {
      drawChooser(ctx);
      canvasChooser.addEventListener(pouch.MOVE, eventChangeColorChooser);
      updateColorChooser(event, canvasChooser, ctx);
      drawChooserSelector(ctx, chooserX.value);
      drawSelector(
        ctxPalette.value,
        ctxPalette.value.canvas.width,
        ctxPalette.value.canvas.height / 2
      );
    });

    canvasChooser.addEventListener(pouch.STOP, (event: any) => {
      canvasChooser.removeEventListener(pouch.MOVE, eventChangeColorChooser);
      updateColorChooser(event, canvasChooser, ctx);
      drawChooser(ctx);
      drawChooserSelector(ctx, chooserX.value);
      drawSelector(
        ctxPalette.value,
        ctxPalette.value.canvas.width,
        ctxPalette.value.canvas.height / 2
      );
    });
  });
};

const drawChooser = (ctx: any) => {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

  const gradient = ctx.createLinearGradient(0, 0, ctx.canvas.width, 0);

  gradient.addColorStop(0, "rgb(255, 0, 0)");
  gradient.addColorStop(0.15, "rgb(255, 0, 255)");
  gradient.addColorStop(0.33, "rgb(0, 0, 255)");
  gradient.addColorStop(0.49, "rgb(0, 255, 255)");
  gradient.addColorStop(0.67, "rgb(0, 255, 0)");
  gradient.addColorStop(0.84, "rgb(255, 255, 0)");
  gradient.addColorStop(1, "rgb(255, 0, 0)");

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
};

const getPixelRatio = (ctx: any) => {
  const dpr = window.devicePixelRatio || 1;
  const bsr =
    ctx.webkitBackingStorePixelRatio ||
    ctx.mozBackingStorePixelRatio ||
    ctx.msBackingStorePixelRatio ||
    ctx.oBackingStorePixelRatio ||
    ctx.backingStorePixelRatio ||
    1;
  return dpr / bsr;
};

const updateColorChooser = (event: any, canvas: any, context: any) => {
  color.value = colorFromChooser.value = getColor(event, canvas, context, true);
  // emits("colorChanged", color.value);
  drawPalette(color.value);
};

const updateColor = (event: any, canvas: any, context: any) => {
  color.value = getColor(event, canvas, context, false);
  // emits("colorChanged", color.value);
};

const getColor = (event: any, canvas: any, context: any, fromChooser: any) => {
  const bounding = canvas.getBoundingClientRect();
  const touchX =
    event.pageX ||
    (event.touches && event.touches[0] && event.touches[0].pageX) ||
    (event.changedTouches && event.changedTouches[0].screenX);
  const touchY =
    event.pageY ||
    (event.touches && event.touches[0] && event.touches[0].pageY) ||
    (event.changedTouches && event.changedTouches[0].screenX);

  const x = (touchX - bounding.left) * getPixelRatio(context);
  const y = (touchY - bounding.top) * getPixelRatio(context);

  if (fromChooser) {
    chooserX.value = x;
  } else {
    paletteX.value = x;
    paletteY.value = y;
  }

  const imageData = context.getImageData(x, y, 1, 1);
  const red = imageData.data[0];
  const green = imageData.data[1];
  const blue = imageData.data[2];
  return `#${toHex(red)}${toHex(green)}${toHex(blue)}`;
};

const toHex = (n: any) => {
  n = parseInt(n, 10);
  if (isNaN(n)) return "00";
  n = Math.max(0, Math.min(n, 255));
  return `0123456789ABCDEF`.charAt((n - (n % 16)) / 16) + `0123456789ABCDEF`.charAt(n % 16);
};

onMounted(() => {});
function onWillPresent() {
  if (props.hexColor) {
    color.value = colorFromChooser.value = props.hexColor;
  } else {
    color.value = colorFromChooser.value = "#0000FF";
  }
  initChooser();
  initPalette();
}

watch(
  () => props.hexColor,
  (newVal) => {
    if (newVal) {
      colorFromChooser.value = newVal;
      drawPalette(colorFromChooser.value);
    }
  }
);

const confirm = () => {
  emits("colorChanged", color.value);
  modal.value.$el!.dismiss();
};
const cancel = () => {
  modal.value.$el!.dismiss();
};
</script>
