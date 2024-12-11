<script lang="ts">
import axios from "axios";
// const URL = "https://3ft23fh89533.vicp.fun/api";
// natapp.cn
// 最新域名： cat /usr/env/natapp/log/natapp.log
const URL = "http://ywcqqu.natappfree.cc/api";
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

export function setSave(
  id: number,
  user: string,
  data: string,
  f_succ: (res: any) => void,
  f_fail: (res: any) => void
) {
  axios
    .post(URL + "/setSave", {
      id: id,
      user_name: user,
      data: data,
      version: 1,
    })
    .then((res) => {
      f_succ(res);
    })
    .catch((err) => {
      f_fail(err);
    });
}
export default {
  getSave,
  setSave,
};
</script>
