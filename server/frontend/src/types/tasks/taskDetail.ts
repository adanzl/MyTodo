
export interface TaskDetail {
  // key  为 material_id
  // value 为 素材进度map
  //   进度map 的 key 为第x天，如果有1则表示那天完成了
  progress: Record<string, Record<string, number>>;
}
