import axios from "axios";
// const URL = "https://3ft23fh89533.vicp.fun/api";
// natapp.cn
// 最新域名： cat /usr/env/natapp/log/natapp.log
const URL_LIST = ["http://kefrw5.natappfree.cc/api", "http://192.168.50.184:9527/api"];
let URL = "http://kefrw5.natappfree.cc/api";
// const URL = "http://192.168.50.184:9527/api";

function checkAddress(url: string) {
  return axios
    .create({
      timeout: 200,
    })
    .head(url + "/")
    .then((response) => {
      return response.status >= 200 && response.status < 300;
    })
    .catch(() => {
      return false;
    });
}
for (const url of URL_LIST) {
  checkAddress(url).then((ret) => {
    if (ret) {
      console.log("use url:", url, ret);
      URL = url;
    }
  });
}
export function getSave(id: number) {
  return new Promise((resolve, reject) => {
    axios
      .get(URL + "/getSave", { params: { id: id } })
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
      });
  });
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
