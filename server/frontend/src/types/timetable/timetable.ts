/**
 * 课程表相关类型定义
 */

/**
 * 课程颜色ID
 */
export type CourseColorId = 1 | 2 | 3 | 4 | 5;

/**
 * 课程颜色配置
 */
export interface CourseColor {
  bg: string;
  border: string;
  hover: string;
}

/**
 * 课程数据
 */
export interface Course {
  /**
   * 开始时间（HH:MM格式，如 "09:00"）
   */
  startTime: string;
  /**
   * 课程名称
   */
  name: string;
  /**
   * 持续时间（分钟）
   */
  duration: number;
  /**
   * 颜色ID（1-5，默认为1）
   */
  colorId?: CourseColorId;
}

/**
 * 编辑中的课程（包含编辑所需的额外信息）
 */
export interface EditingCourse extends Course {
  /**
   * 星期几（如 "周一"）
   */
  day: string;
  /**
   * 孩子标识（"zhaozhao" | "cancan"）
   */
  child: "zhaozhao" | "cancan";
  /**
   * 原始开始时间（用于编辑时检查冲突）
   */
  originalStartTime?: string | null;
}

/**
 * 课程表数据格式
 * key: "周一-zhaozhao" | "周一-cancan" 等
 * value: 该时间段的课程列表
 */
export type TimetableData = Record<string, Course[]>;

/**
 * 筛选模式
 */
export type FilterChild = "all" | "zhaozhao" | "cancan";

/**
 * 星期数组
 */
export type Weekday = "周一" | "周二" | "周三" | "周四" | "周五" | "周六" | "周日";

