/**
 * 用户数据模型
 */
export class User {
  id: number = -1;
  name: string = "";
  pwd: string = "";
  icon: string = "";
  admin: number = 0;
  score: number = 0;

  constructor() {
    this.id = -1;
    this.name = "";
    this.pwd = "";
    this.icon = "";
    this.admin = 0;
    this.score = 0;
  }
}
