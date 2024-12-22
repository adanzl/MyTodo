import LocalCache from "./LocalCache";
import { getPic, setPic } from "./NetUtil";

export async function getImage(id: number) {
  let ret = LocalCache.get<string>("img_" + id);
  if (ret === null) {
    ret = await getPic(id);
    if (ret) {
      LocalCache.set("img_" + id, ret, 10 * 60);
    }
  }
  return ret;
}

export async function setImage(id: number | undefined, data: string) {
  console.log("setImage", id, data);
  const ret = await setPic(id, data);
  LocalCache.remove("img_" + id);
  return ret;
}

export default {
  getImage,
  setImage,
};
