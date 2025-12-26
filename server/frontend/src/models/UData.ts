/**
 * 用户数据处理工具类
 */
import dayjs, { type Dayjs } from "dayjs";
import * as _ from "lodash-es";
import { getUserInfo, setUserInfo } from "@/api/user";
import { ScheduleData } from "./ScheduleData";
import { Subtask } from "./Subtask";
import { S_TS } from "@/utils/date";
import type { UserData } from "./UserData";
import type { ScheduleSave } from "./ScheduleSave";

export class UData {
  static CmpScheduleData(
    a: ScheduleData,
    b: ScheduleData,
    save?: Record<number, ScheduleSave>
  ): number {
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

  static CmpScheduleSubtasks(a: Subtask, b: Subtask, save?: ScheduleSave): number {
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
  static setScheduleSave(
    dKey: string,
    userData: UserData,
    _scheduleData: ScheduleData,
    _scheduleSave: ScheduleSave
  ): void {
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
      _.forEach(_scheduleData.subtasks, (v: Subtask) => {
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
        _scheduleSave.score = (_scheduleSave.score || 0) - (_scheduleData.score ?? 0);
      }
    }
    // 变更积分 只能给日程的所有者加积分
    if (dScore !== 0) {
      // GlobalVar.user.score += dScore;
      getUserInfo(userData.userId).then(userInfo => {
        userInfo.score += dScore;
        setUserInfo(userData.userId, userInfo.score).then(() => {
          //   EventBus.$emit(C_EVENT.UPDATE_USER_INFO);
        });
      });
    }
  }

  /**
   * 更新日程数据
   */
  static updateSchedularData(
    userData: UserData,
    _scheduleData: ScheduleData,
    _scheduleSave: ScheduleSave,
    dt: Dayjs,
    type: "all" | "cur"
  ): boolean {
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
        const idx = userData.schedules.findIndex(s => s.id === _scheduleData.id);
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

  static parseScheduleData(jsonStr: string): ScheduleData {
    const ret = JSON.parse(jsonStr) as ScheduleData;
    ret.startTs = ret.startTs ? dayjs(ret.startTs) : undefined;
    ret.endTs = ret.endTs ? dayjs(ret.endTs) : undefined;
    ret.repeatEndTs = ret.repeatEndTs ? dayjs(ret.repeatEndTs) : undefined;
    return ret;
  }

  static parseUserData(userDataStr: string): UserData {
    const ret = JSON.parse(userDataStr) as UserData;
    if (ret.schedules === undefined) {
      ret.schedules = [];
    }
    if (ret.save === undefined) {
      ret.save = {};
    }
    for (let i = 0; i < ret.schedules.length; i++) {
      const schedule = ret.schedules[i];
      schedule.startTs = schedule.startTs ? dayjs(schedule.startTs) : undefined;
      schedule.endTs = schedule.endTs ? dayjs(schedule.endTs) : undefined;
      schedule.repeatEndTs = schedule.repeatEndTs ? dayjs(schedule.repeatEndTs) : undefined;
      if (schedule.subtasks === undefined) {
        schedule.subtasks = [];
      }
    }
    return ret;
  }

  static CountScheduleReward(schedule: ScheduleData): number {
    return (
      (schedule.subtasks?.reduce((sum, t) => {
        return sum + (t.score ?? 0);
      }, 0) || 0) + (schedule.score ?? 0)
    );
  }
}
