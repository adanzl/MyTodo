import axios from "axios";
// const URL = "https://3ft23fh89533.vicp.fun/api";
// natapp.cn
// 最新域名： cat /usr/env/natapp/log/natapp.log
const REMOTE = { url: "http://2kutu3.natappfree.cc/api", available: false };
// const LOCAL = { url: "http://192.168.50.184:9527/api", available: false };
const LOCAL = { url: "http://localhost:8888", available: false };
let URL = "http://2kutu3.natappfree.cc/api";
// const URL = "http://192.168.50.184:9527/api";

async function checkAddress(url: string) {
  try {
    const response = await axios
      .create({
        timeout: 200,
      })
      .head(url + "/");
    return response.status >= 200 && response.status < 300;
  } catch {
    return false;
  }
}

await checkAddress(REMOTE.url).then((ret) => {
  if (ret && !LOCAL.available) {
    REMOTE.available = true;
    console.log("use url:", REMOTE.url);
    URL = REMOTE.url;
  }
});
await checkAddress(LOCAL.url).then((ret) => {
  if (ret) {
    LOCAL.available = true;
    console.log("use url:", LOCAL.url, ret);
    URL = LOCAL.url;
  }
});
export async function getSave(id: number) {
  if (id === undefined) {
    throw new Error("id is undefined");
  }
  const rsp: any = await axios.get(URL + "/getSave", { params: { id: id } });
  // console.log(rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export function setSave(id: number | undefined, user: string, data: string) {
  console.log(data);
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
export default {
  getSave,
  setSave,
};
