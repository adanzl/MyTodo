import axios from "axios";
// const URL = "https://3ft23fh89533.vicp.fun/api";
// natapp.cn
// 最新域名： cat /usr/env/natapp/log/natapp.log
const REMOTE = { url: "http://cm9ic5.natappfree.cc/api", available: false };
const LOCAL = { url: "http://192.168.50.184:9527/api", available: false };
// const LOCAL = { url: "http://localhost:8888", available: false };
let URL = "";
// const URL = "http://192.168.50.184:9527/api";

async function checkAddress(url: string) {
  try {
    const response = await axios
      .create({
        timeout: 1000,
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
  const b2 = await checkAddress(LOCAL.url).then((ret) => {
    if (ret) {
      LOCAL.available = true;
      console.log("use url:", LOCAL.url, ret);
      URL = LOCAL.url;
    }
    return ret;
  });
  console.log("init net ", b1, b2);
}
export async function getSave(id: number) {
  if (id === undefined) {
    throw new Error("id is undefined");
  }
  const rsp: any = await axios.get(URL + "/getSave", { params: { id: id } });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export function setSave(id: number | undefined, user: string, data: string) {
  // console.log(data);
  return new Promise((resolve, reject) => {
    if (id === undefined) {
      reject(new Error("id is undefined"));
      return;
    }
    axios
      .post(URL + "/setSave", {
        id: id,
        user: user,
        data: data,
        version: 1,
      })
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
      });
  });
}

export async function setPic(id: number | undefined, data: string): Promise<string> {
  const rsp: any = await axios.post(URL + "/setPic", {
    id: id,
    data: data,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function delPic(id: number) {
  const rsp: any = await axios.post(URL + "/delPic", {
    id: id,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getPicList(pageNum?: number, pageSize?: number) {
  const rsp: any = await axios.get(URL + "/getAllPic", {
    params: { pageNum: pageNum, pageSize: pageSize },
  });
  // console.log(rsp.data.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export async function getPic(id: number): Promise<string> {
  const rsp: any = await axios.get(URL + "/getPic", { params: { id: id } });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export default {
  getSave,
  setSave,
  getPicList,
  getPic,
  setPic,
  delPic,
  initNet,
};
