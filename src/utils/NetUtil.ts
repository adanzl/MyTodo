import { LoadColorData } from "@/modal/ColorType";
import { UData } from "@/modal/UserData";
import EventBus, { C_EVENT } from "@/modal/EventBus";
import axios from "axios";
// const URL = "https://3ft23fh89533.vicp.fun/api";
// natapp.cn
// 最新域名： cat /usr/env/natapp/log/natapp.log
const REMOTE = { url: "https://leo-zhao.natapp4.cc/api", available: false };
const LOCAL = { url: "http://192.168.50.184:9527/api", available: false };
// const LOCAL = { url: "http://localhost:8888", available: false };
let URL = "";
// const URL = "http://192.168.50.184:9527/api";

async function checkAddress(url: string, timeout: number = 10000) {
  try {
    const response = await axios
      .create({
        timeout: timeout,
      })
      .head(url + "/");
    return response.status >= 200 && response.status < 300;
  } catch {
    return false;
  }
}

export async function initNet(): Promise<void> {
  const b1 = await checkAddress(REMOTE.url).then((ret) => {
    if (ret && !LOCAL.available) {
      REMOTE.available = true;
      console.log("use url:", REMOTE.url);
      URL = REMOTE.url;
    }
    return ret;
  });
  const b2 = await checkAddress(LOCAL.url, 100).then((ret) => {
    if (ret) {
      LOCAL.available = true;
      console.log("use url:", LOCAL.url, ret);
      URL = LOCAL.url;
    }
    return ret;
  });
  console.log("init net ", b1, b2);
  LoadColorData();
}
export async function getSave(id: number) {
  if (id === undefined) {
    throw new Error("id is undefined");
  }
  const rsp: any = await axios.get(URL + "/getData", {
    params: { id: id, table: "t_schedule", idx: 2 },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  const ret = UData.parseUserData(rsp.data.data);
  EventBus.$emit(C_EVENT.UPDATE_SAVE, ret);
  return ret;
}

export function setSave(id: number | undefined, data: any) {
  // console.log(data);
  return new Promise((resolve, reject) => {
    if (id === undefined) {
      reject(new Error("id is undefined"));
      return;
    }
    axios
      .post(URL + "/setData", {
        table: "t_schedule",
        data: data,
      })
      .then((res: any) => {
        if (res.data.code === 0) {
          resolve(res);
          EventBus.$emit(C_EVENT.UPDATE_SAVE, data);
        } else {
          reject(new Error(res.data.msg));
        }
      })
      .catch((err: any) => {
        reject(err);
      });
  });
}

export async function setUserInfo(id: number | undefined, score: number) {
  const rsp: any = await axios.post(URL + "/setData", {
    table: "t_user",
    data: {
      id: id,
      score: score,
    },
  });
  console.log("setUserInfo", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setPic(id: number | undefined, data: string): Promise<string> {
  const rsp: any = await axios.post(URL + "/setData", {
    table: "t_user_pic",
    data: {
      id: id,
      data: data,
    },
  });
  console.log("setPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function delPic(id: number) {
  const rsp: any = await axios.post(URL + "/delData", {
    id: id,
    table: "t_user_pic",
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getScheduleList() {
  const rsp: any = await axios.get(URL + "/getAll", {
    params: { table: "t_schedule", fields: "id, name, user_id" },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getUserList() {
  const rsp: any = await axios.get(URL + "/getAll", {
    params: { table: "t_user" },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setUserData(data: any) {
  const rsp: any = await axios.post(URL + "/setData", {
    table: "t_user",
    data: data,
  });
  console.log("setUser", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getPicList(pageNum?: number, pageSize?: number) {
  const rsp: any = await axios.get(URL + "/getAll", {
    params: { table: "t_user_pic", pageNum: pageNum, pageSize: pageSize },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function getPic(id: number): Promise<string> {
  const rsp: any = await axios.get(URL + "/getData", { params: { table: "t_user_pic", id: id } });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getColorList(pageNum?: number, pageSize?: number) {
  const rsp: any = await axios.get(URL + "/getAll", {
    params: { table: "t_colors", pageNum: pageNum, pageSize: pageSize },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setColor(
  id: number | undefined,
  name: string,
  color: string
): Promise<string> {
  const rsp: any = await axios.post(URL + "/setData", {
    table: "t_colors",
    data: { id: id, name: name, color: color },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function delColor(id: number) {
  const rsp: any = await axios.post(URL + "/delData", {
    id: id,
    table: "t_colors",
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export default {};
