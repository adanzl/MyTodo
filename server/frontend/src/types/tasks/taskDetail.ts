export interface TaskDetail {
  // 每日素材配置
  // key: 天数索引（从0开始）
  // value: 该天的素材列表
  dailyMaterials: Record<
    string,
    Array<{
      id: number;
      name: string;
      type: number;
      status?: number; // 1表示完成，0或未定义表示未完成
    }>
  >;
}
