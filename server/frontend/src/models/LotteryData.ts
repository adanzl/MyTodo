/**
 * 抽奖数据模型
 */
export class LotteryData {
  id: number = -1;
  name: string = "";
  imgId?: number;
  img?: string;
  weight: number = 1;
  highlight: boolean = false;

  constructor() {
    this.id = -1;
    this.name = "";
    this.imgId = undefined;
    this.img = undefined;
    this.weight = 1;
    this.highlight = false;
  }
}


