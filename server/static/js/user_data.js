import { RepeatData } from "./schedule_type.js";
import { getUserInfo, setUserInfo } from "./net_util.js";
const dayjs = window.dayjs;
const _ = window._;

export class User {
  constructor() {
    this.id = -1;
    this.name = "";
    this.pwd = "";
    this.icon = "";
    this.admin = 0;
    this.score = 0;
  }
}

export class LotteryData {
  constructor() {
    this.id = -1;
    this.name = "";
    this.imgId = undefined;
    this.img = undefined;
    this.weight = 1;
    this.highlight = false;
  }
}

export class Subtask {
  constructor() {
    this.id = -1;
    this.name = "";
    this.order = 0;
    this.score = 0;
    this.imgIds = []; // 图片id列表
  }

  static Copy(o) {
    return {
      id: o.id,
      name: o.name,
      order: o.order,
      score: o.score,
      imgIds: o.imgIds?.concat(),
    };
  }
}

// 日程计划数据
export class ScheduleData {
  constructor() {
    // ===== 日程数据 =====
    this.id = -1; // 任务id
    this.startTs = undefined; // 开始时间
    this.endTs = undefined; // 结束时间
    this.allDay = true; // 是否全天
    this.reminder = 0; // 提醒类型
    this.repeat = 0; // 重复类型
    this.repeatData = new RepeatData(); // 重复数据
    this.repeatEndTs = undefined; // 重复结束类型
    // 以下字段为覆盖字段，用于覆盖默认值
    this.title = undefined; // 任务标题
    this.color = 0; // 颜色id
    this.priority = -1; // 优先级
    this.groupId = -1; // 分组id
    this.order = 0; // 排序 数字越大越靠后
    this.score = undefined; // 积分
    this.subtasks = []; // 子任务列表
    this.startTs = dayjs().startOf("day");
    this.endTs = dayjs().startOf("day");
  }

  static Copy(o) {
    const ret = JSON.parse(JSON.stringify(o));
    ret.startTs = ret.startTs && dayjs(ret.startTs);
    ret.endTs = ret.endTs && dayjs(ret.endTs);
    ret.repeatEndTs = ret.repeatEndTs && dayjs(ret.repeatEndTs);
    ret.subtasks = [];
    if (o.subtasks) {
      for (const subtask of o.subtasks) {
        ret.subtasks.push(Subtask.Copy(subtask));
      }
    }
    return ret;
  }
}

// 日程存档【每天】
export class ScheduleSave {
  constructor() {
    this.state = 0;
    this.subtasks = {}; // <number, number>;
    // 覆盖字段
    this.scheduleOverride = undefined;
    this.score = undefined; // 通过这个任务获得的积分
  }

  static Copy(o) {
    const ret = new ScheduleSave();
    ret.state = o.state;
    ret.score = o.score;
    if (o.scheduleOverride) ret.scheduleOverride = ScheduleData.Copy(o.scheduleOverride);
    if (o.subtasks) ret.subtasks = JSON.parse(JSON.stringify(o.subtasks));
    return ret;
  }
}

// 用户数据
export class UserData {
  constructor() {
    this.id = -1; // 存档id
    this.name = ""; // 存档名称
    this.userId = -1; // 用户id
    this.schedules = []; // 日程计划列表
    // 计划完成情况  日期->对应日期完成情况(任务id->完成情况)
    this.save = {};
  }

  static Copy(o) {
    const ret = new UserData();
    ret.id = o.id;
    ret.name = o.name;
    ret.schedules = [];
    for (const schedule of o.schedules) {
      ret.schedules.push(ScheduleData.Copy(schedule));
    }
    ret.save = JSON.parse(JSON.stringify(o.save));
    return ret;
  }
}

// 一天的数据
export class DayData {
  constructor(_dt) {
    this.dt = _dt || dayjs().startOf("day");
    this.events = []; // 当天可见日程
    this.save = undefined; // 日程id->日程保存情况
  }
}

// 一个月的数据
export class MonthData {
  constructor() {
    this.vid = 0;
    this.month = 0;
    this.year = 0;
    this.firstDayOfMonth = dayjs().startOf("day");
    this.weekArr = [];
  }
}

export class UData {
  static CmpScheduleData(a, b, save) {
    // 状态
    const sa = (save && save[a.id]?.state) ?? 0;
    const sb = (save && save[b.id]?.state) ?? 0;
    if (sa !== sb) {
      return sa - sb;
    }
    // order
    const oa = a.order ?? 99999;
    const ob = b.order ?? 99999;
    if (oa !== ob) {
      return oa - ob;
    }
    return (a.id ?? 0) - (b.id ?? 0);
  }

  static CmpScheduleSubtasks(a, b, save) {
    // 状态
    const sa = (save && save.subtasks && save.subtasks[a.id]) ?? 0;
    const sb = (save && save.subtasks && save.subtasks[b.id]) ?? 0;
    if (sa !== sb) {
      return sa - sb;
    }
    // order
    const oa = a.order ?? 99999;
    const ob = b.order ?? 99999;
    if (oa !== ob) {
      return oa - ob;
    }
    return (a.id ?? 0) - (b.id ?? 0);
  }

  // 设置日程存档，要同步奖励积分
  static setScheduleSave(dKey, userData, _scheduleData, _scheduleSave) {
    if (!(dKey in userData.save)) {
      userData.save[dKey] = {};
    }
    const map = userData.save[dKey];
    map[_scheduleData.id] = _scheduleSave;
    const oriScore = _scheduleSave.score ?? 0; // 表示已经给的积分
    let dScore = 0; // 要变更的积分
    if (_scheduleSave.state === 1) {
      let newScore = _scheduleData.score ?? 0;
      // 处理子任务
      _.forEach(_scheduleData.subtasks, (v) => {
        newScore += v.score ?? 0;
        _scheduleSave.subtasks[v.id] = 1;
      });
      // +积分
      if (newScore > oriScore) {
        dScore += newScore - oriScore;
        _scheduleSave.score = newScore;
        // EventBus.$emit(C_EVENT.REWARD, newScore - oriScore);
      }
    } else {
      // -积分 减积分的地方 只核减任务的主积分
      if (_scheduleSave.score) {
        dScore -= _scheduleData.score ?? 0;
        _scheduleSave.score -= _scheduleData.score ?? 0;
      }
    }
    // 变更积分 只能给日程的所有者加积分
    if (dScore !== 0) {
      // GlobalVar.user.score += dScore;
      getUserInfo(userData.userId).then((userInfo) => {
        userInfo.score += dScore;
        setUserInfo(userData.userId, userInfo.score).then(() => {
        //   EventBus.$emit(C_EVENT.UPDATE_USER_INFO);
        });
      });
    }
  }

  /**
   * 更新日程数据
   * @param userData 用户数据
   * @param _scheduleData 新的日程数据
   * @param _scheduleSave 新的日程存档数据
   * @param dt 当前日期
   * @param type 更新类型 all:更新日程和存档 cur:更新存档
   * @returns 是否更新成功
   */
  static updateSchedularData(userData, _scheduleData, _scheduleSave, dt, type) {
    const dKey = S_TS(dt);
    if (type === "all") {
      // console.log("updateSchedularData", _scheduleData, _scheduleSave);
      // 日程变化
      if (_scheduleData.id === -1) {
        // add id userData.value.schedules id的最大值=1
        const id = userData.schedules.reduce((max, s) => (s.id > max ? s.id : max), 0) + 1;
        _scheduleData.id = id;
        userData.schedules.push(_scheduleData);
      } else {
        const idx = userData.schedules.findIndex((s) => s.id === _scheduleData.id);
        if (idx !== -1) {
          userData.schedules[idx] = _scheduleData;
        }
      }
      // 存档变化
      UData.setScheduleSave(dKey, userData, _scheduleData, _scheduleSave);
    } else if (type === "cur") {
      // 只管当天日程
      // 存档变化
      UData.setScheduleSave(dKey, userData, _scheduleData, _scheduleSave);
      _scheduleSave.scheduleOverride = _scheduleData;
    } else {
      return false;
    }
    return true;
  }

  static parseScheduleData(jsonStr) {
    const ret = JSON.parse(jsonStr);
    ret.startTs = dayjs(ret.startTs);
    ret.endTs = dayjs(ret.endTs);
    ret.repeatEndTs = ret.repeatEndTs && dayjs(ret.repeatEndTs);
    return ret;
  }

  static parseUserData(userDataStr) {
    const ret = JSON.parse(userDataStr);
    if (ret.schedules === undefined) {
      ret.schedules = [];
    }
    if (ret.save === undefined) {
      ret.save = {};
    }
    for (let i = 0; i < ret.schedules.length; i++) {
      const schedule = ret.schedules[i];
      schedule.startTs = dayjs(schedule.startTs);
      schedule.endTs = dayjs(schedule.endTs);
      schedule.repeatEndTs = schedule.repeatEndTs && dayjs(schedule.repeatEndTs);
      if (schedule.subtasks === undefined) {
        schedule.subtasks = [];
      }
    }
    return ret;
  }

  static CountScheduleReward(schedule) {
    return (
      (schedule.subtasks?.reduce((sum, t) => {
        return sum + (t.score ?? 0);
      }, 0) || 0) + (schedule.score ?? 0)
    );
  }
}

export const S_TS = (dt) => {
  if (dt === undefined) return "";
  return dt.format("YYYY-MM-DD");
};

export default {};
