<script lang="ts">
import axios from "axios";
// const URL = "https://3ft23fh89533.vicp.fun/api";
// natapp.cn
// 最新域名： cat /usr/env/natapp/log/natapp.log
const URL = "http://8hc2x8.natappfree.cc/api";
// const URL = "http://192.168.50.184:9527/api";
export function getSave(
  id: number,
  f_succ: (res: any) => void,
  f_fail: (res: any) => void
) {
  axios
    .get(URL + "/getSave", { params: { id: id } })
    .then((res) => {
      f_succ(res);
    })
    .catch((err) => {
      f_fail(err);
    });
}

export function setSave(id: number | undefined, user: string, data: string) {
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
</script>
