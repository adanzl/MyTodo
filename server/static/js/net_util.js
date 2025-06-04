import { UData } from "./user_data.js";
const axios = window.axios;
const REMOTE = { url: "https://leo-zhao.natapp4.cc/api", available: true };
const API_URL = REMOTE.url;

// export function getApiUrl() {
//   return REMOTE;
// }

export async function getSave(id) {
  if (id === undefined) {
    throw new Error("id is undefined");
  }

  const rsp = await axios.get(API_URL + "/getData", {
    params: { id, table: "t_schedule", fields: "data,user_id" },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  const ret = UData.parseUserData(rsp.data.data.data);
  ret.userId = rsp.data.data.user_id;
  return ret;
}

// export function setSave(id, data) {
//   return new Promise((resolve, reject) => {
//     if (id === undefined) {
//       reject(new Error("id is undefined"));
//       return;
//     }

//     axios
//       .post(API_URL + "/setData", {
//         table: "t_schedule",
//         data: { id, data: JSON.stringify(data) },
//       })
//       .then((res) => {
//         if (res.data.code === 0) {
//           resolve(res);
//         } else {
//           reject(new Error(res.data.msg));
//         }
//       })
//       .catch((err) => {
//         reject(err);
//       });
//   });
// }

export async function setUserInfo(id, score) {
  const rsp = await axios.post(API_URL + "/setData", {
    table: "t_user",
    data: { id, score },
  });

  console.log("setUserInfo", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

// export async function getConversationId(id) {
//   const rsp = await axios.get(API_URL + "/getRdsData", {
//     params: { table: "conversation:id", id },
//   });

//   if (rsp.data.code !== 0) {
//     throw new Error(rsp.data.msg);
//   }

//   return rsp.data.data;
// }

// export async function setConversationId(id, cId) {
//   const rsp = await axios.post(API_URL + "/setRdsData", {
//     table: "conversation:id",
//     data: { id, value: cId },
//   });

//   console.log("setConversationId", rsp.data);
//   if (rsp.data.code !== 0) {
//     throw new Error(rsp.data.msg);
//   }

//   return rsp.data.data;
// }

// export async function getChatSetting(id) {
//   const rsp = await axios.get(API_URL + "/getRdsData", {
//     params: { table: "chatSetting", id },
//   });

//   if (rsp.data.code !== 0) {
//     throw new Error(rsp.data.msg);
//   }

//   return rsp.data.data;
// }

// export async function setChatSetting(id, cId) {
//   const rsp = await axios.post(API_URL + "/setRdsData", {
//     table: "chatSetting",
//     data: { id, value: cId },
//   });

//   console.log("setChatSetting", rsp.data);
//   if (rsp.data.code !== 0) {
//     throw new Error(rsp.data.msg);
//   }

//   return rsp.data.data;
// }

export async function getUserInfo(id) {
  const rsp = await axios.get(API_URL + "/getData", {
    params: { table: "t_user", id, fields: "id,score" },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

// export async function getScheduleList() {
//   const rsp = await axios.get(API_URL + "/getAll", {
//     params: { table: "t_schedule", fields: "id,name,user_id" },
//   });

//   if (rsp.data.code !== 0) {
//     throw new Error(rsp.data.msg);
//   }

//   return rsp.data.data;
// }

/**
 * 获取数据
 * @param {*} fields 字段
 */
export async function getData(table, id, fields) {
  const rsp = await axios.get(API_URL + "/getData", {
    params: { table: table, id: id, fields: fields },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/**
 * 获取数据列表
 */
export async function getList(table, conditions, pageNum, pageSize) {
  const rsp = await axios.get(API_URL + "/getAll", {
    params: {
      table: table,
      conditions: conditions ? JSON.stringify(conditions) : undefined,
      pageNum,
      pageSize,
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}
/**
 * 设置数据
 */
export async function setData(table, data) {
  if (data.id) {
    if (data.id === -1) {
      data.id = null;
    }
  }
  const rsp = await axios.post(API_URL + "/setData", {
    table: table,
    data,
  });

  console.log("setData", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}
export async function delData(table, id) {
  const rsp = await axios.post(API_URL + "/delData", {
    id,
    table,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

/**
 * 变更积分
 * @param {*} user id
 * @param {*} action 行为
 * @param {*} value 分值
 * @param {*} msg 备注
 * @returns
 */
export async function addScore(user, action, value, msg) {
  const rsp = await axios.post(API_URL + "/addScore", {
    user,
    action,
    value,
    msg,
  });

  console.log("addScore", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}
export default {};
