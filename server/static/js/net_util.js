import { UData } from "./user_data.js";
const axios = window.axios;
const REMOTE = { url: "https://leo-zhao.natapp4.cc/api", available: true };
const API_URL = REMOTE.url;
export function getApiUrl() {
  return API_URL;
}
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

export async function getUserInfo(id) {
  const rsp = await axios.get(API_URL + "/getData", {
    params: { table: "t_user", id, fields: "id,score" },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

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

/**
 * 获取rds列表数据
 */
export async function getRdsList(key, startId, pageSize) {
  const rsp = await axios.get(API_URL + "/getRdsList", {
    params: { key: key, pageSize: pageSize, startId: startId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/**
 * 获取rds数据
 */
export async function getRdsData(table, id) {
  const rsp = await axios.get(API_URL + "/getRdsData", {
    params: { table: table, id: id },
  });
  // console.log("getPic", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
export default {};
