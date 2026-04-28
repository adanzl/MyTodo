export interface TaskDetail {
  // 每日素材配置
  // key: 天数索引（从0开始）
  // value: 该天的素材列表，每个素材包含id、name、type和status字段
  dailyMaterials: Record<
    string,
    Array<{
      id: number;
      name: string;
      type: number;
      status?: Record<string, number>; // key: user_id, value: 1表示完成，0或未定义表示未完成
    }>
  >;
  // 每日分数配置
  // key: 天数索引（从0开始）
  // value: 该天的分数，完成当天全部素材可获得
  dailyScore: Record<string, number>;
}
