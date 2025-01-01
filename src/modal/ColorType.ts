import { getColorList } from "@/utils/NetUtil";
import EventBus from "@/modal/EventBus";

export interface ColorType {
  id: number;
  label: string;
  tag: string;
}
// 颜色类型
export const ColorOptions: ColorType[] = [
  { id: 0, label: "None", tag: "#f8fafc" },
  { id: 1, label: "Red", tag: "#fca5a5" },
  { id: 2, label: "Yellow", tag: "#fde047" },
  { id: 3, label: "Blue", tag: "#93c5fd" },
  { id: 4, label: "Green", tag: "#4ade80" },
];

export async function LoadColorData() {
  return new Promise((resolve) => {
    getColorList(1, 30).then((res) => {
      console.log("LoadColorData", res);
      ColorOptions.splice(0, ColorOptions.length);
      res.data.forEach((e: any) => {
        ColorOptions.push({
          id: e.id,
          label: e.name,
          tag: e.color,
        });
      });
      EventBus.$emit("updateColor", ColorOptions);
      resolve(ColorOptions);
    });
  });
}

export const getColorOptions = (id?: number): ColorType => {
  for (const v of ColorOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return ColorOptions[0];
};

export default {
  ColorOptions,
  getColorOptions,
};
