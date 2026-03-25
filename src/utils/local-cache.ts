export class LocalCache {
  /**
   * 设置缓存项。
   * @param key 键。
   * @param value 值。
   * @param ttl 过期时间（秒）。
   */
  static set(key: string, value: any, ttl: number): void {
    const expires = Date.now() + ttl * 1000; // 将过期时间转换为毫秒
    localStorage.setItem(key, JSON.stringify({ value, expires }));
  }

  /**
   * 获取缓存项
   * @param key 键
   * @returns
   */
  static get<T>(key: string): T | null {
    const item = JSON.parse(localStorage.getItem(key) || "null");
    if (item && item.expires > Date.now()) {
      return item.value as T;
    }
    this.remove(key);
    return null;
  }

  // 删除缓存项
  static remove(key: string): void {
    localStorage.removeItem(key);
  }

  // 检查缓存项是否存在
  static has(key: string): boolean {
    return !!this.get(key);
  }
}


export default LocalCache;
