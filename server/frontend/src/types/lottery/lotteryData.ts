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

/**
 * 奖品接口
 */
export interface Gift {
  id: number;
  name: string;
  img: string;
  cate_id?: number;
  pool_id?: number;
  cost: number;
  enable: boolean | number;
  exchange: number;
  stock: number;
  wish: boolean | number;
  show: boolean | number;
  edited?: boolean;
}

/**
 * 奖品 API 数据接口
 */
export interface GiftApiData {
  id: number;
  name: string;
  image: string;
  cate_id?: number;
  pool_id?: number;
  cost: number;
  enable: number;
  exchange?: number;
  stock?: number;
  wish?: number;
  show?: number;
}

/**
 * 奖品分类接口
 */
export interface GiftCategory {
  id: number;
  name: string;
  edited?: boolean;
}
