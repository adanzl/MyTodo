/**
 * 子任务数据模型
 */
export class Subtask {
  id: number = -1;
  name: string = "";
  order: number = 0;
  score: number = 0;
  imgIds: number[] = []; // 图片id列表

  constructor() {
    this.id = -1;
    this.name = "";
    this.order = 0;
    this.score = 0;
    this.imgIds = [];
  }

  static Copy(o: Subtask): Subtask {
    return {
      id: o.id,
      name: o.name,
      order: o.order,
      score: o.score,
      imgIds: o.imgIds?.concat() || [],
    };
  }
}


