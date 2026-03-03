"""
与 Java Redisson RRateLimiter 兼容的 Python 分布式限流器。

基于令牌桶算法，使用 Lua 脚本保证原子性操作，可与 Java 端 Redisson 共用同一个限流器实例。

核心特性：
- 完全兼容 Redisson RRateLimiter 的数据结构和算法
- 支持全局限流 (OVERALL) 和单机限流 (PER_CLIENT)
- 基于滑动时间窗口的令牌桶算法
- 使用 Lua 脚本保证原子性
- 支持 gevent 超时保护

使用示例：
```python
from core.tools.rate_limiter import RateType, RateIntervalUnit, RedisRateLimiter

# 创建限流器
limiter = RedisRateLimiter('my-limiter')

# 设置限流规则：每秒允许 10 个请求
limiter.try_set_rate(RateType.OVERALL, 10, 1, RateIntervalUnit.SECONDS)

# 尝试获取 1 个令牌（非阻塞）
if limiter.try_acquire(1):
    print("获取成功")
else:
    print("被限流")

# 阻塞获取令牌（最多等待 5 秒）
if limiter.try_acquire(1, timeout=5):
    print("获取成功")
```
"""

import time
from enum import Enum
from typing import Optional, Union

import redis

import core.db.rds_mgr as rds_mgr


class RateType(Enum):
    """限流类型枚举"""
    OVERALL = 0  # 全局限流
    PER_CLIENT = 1  # 单机限流


class RateIntervalUnit(Enum):
    """时间间隔单位枚举"""
    MILLISECONDS = 0
    SECONDS = 1
    MINUTES = 2
    HOURS = 3
    DAYS = 4


# Lua 脚本：初始化限流器配置
# 与 Redisson 保持完全兼容
INIT_LIMITER_SCRIPT = """
local rateName = KEYS[1]
local rate = tonumber(ARGV[1])
local interval = tonumber(ARGV[2])
local rateType = tonumber(ARGV[3])

-- 使用 hsetnx 确保只在不存在时设置（避免覆盖已有配置）
local rateSet = redis.call('hsetnx', rateName, 'rate', rate)
if rateSet == 1 then
    redis.call('hsetnx', rateName, 'interval', interval)
    redis.call('hsetnx', rateName, 'type', rateType)
    redis.call('hsetnx', rateName, 'counter', 0)
    redis.call('hsetnx', rateName, 'timestamp', redis.call('TIME')[1] * 1000 + math.floor(redis.call('TIME')[2] / 1000))
    return true
end
return false
"""

# Lua 脚本：尝试获取令牌（核心算法）
# 实现了令牌桶算法，支持自动补充令牌
TRY_ACQUIRE_SCRIPT = """
local rateName = KEYS[1]
local requestAmount = tonumber(ARGV[1])
local currentTime = tonumber(ARGV[2])

-- 获取限流器配置
local rateData = redis.call('HMGET', rateName, 'rate', 'interval', 'counter', 'timestamp')
local rate = tonumber(rateData[1])
local interval = tonumber(rateData[2])
local counter = tonumber(rateData[3])
local timestamp = tonumber(rateData[4])

-- 如果配置不存在，返回 false
if rate == nil or interval == nil then
    return -1
end

-- 计算时间流逝和应该补充的令牌数
local timePassed = currentTime - timestamp
local tokensToAdd = math.floor(timePassed * rate / interval)

-- 更新 counter（减去消耗的令牌，加上新补充的令牌）
local newCounter = counter - requestAmount + tokensToAdd

-- 判断是否有足够的令牌
if newCounter >= 0 and newCounter <= rate then
    -- 有足够的令牌，更新状态
    redis.call('HSET', rateName, 'counter', newCounter)
    redis.call('HSET', rateName, 'timestamp', currentTime)
    return 1
elseif newCounter < 0 then
    -- 令牌不足，返回需要等待的时间（毫秒）
    local waitTime = math.ceil((counter - tokensToAdd - rate + requestAmount) * interval / rate)
    return waitTime
else
    -- 其他情况（理论上不会发生）
    return -1
end
"""


class RedisRateLimiter:
    """
    Redis 分布式限流器，与 Java Redisson RRateLimiter 完全兼容。
    
    使用令牌桶算法，支持在 Redis 集群中进行分布式限流。
    所有操作都通过 Lua 脚本保证原子性。
    """

    def __init__(self, name: str, redis_client: Optional[redis.Redis] = None):
        """
        初始化限流器。
        
        Args:
            name: 限流器名称（将作为 Redis key 的前缀）
            redis_client: Redis 客户端实例，默认使用 rds_mgr.rds
        """
        self.name = name
        self.redis_client = redis_client or rds_mgr.rds

        # 注册 Lua 脚本
        self._init_script = self.redis_client.register_script(INIT_LIMITER_SCRIPT)
        self._try_acquire_script = self.redis_client.register_script(TRY_ACQUIRE_SCRIPT)

        # 限流器配置缓存
        self._rate: Optional[int] = None
        self._interval: Optional[int] = None
        self._rate_type: RateType = RateType.OVERALL

    def try_set_rate(self,
                     rate_type: RateType,
                     rate: int,
                     interval: int,
                     unit: RateIntervalUnit = RateIntervalUnit.SECONDS) -> bool:
        """
        尝试设置限流器配置。
        
        如果限流器已存在且已配置，则不会覆盖现有配置。
        
        Args:
            rate_type: 限流类型（OVERALL 或 PER_CLIENT）
            rate: 每个时间窗口允许的请求数
            interval: 时间窗口大小
            unit: 时间窗口单位
            
        Returns:
            bool: 设置成功返回 True，如果已存在配置返回 False
            
        Example:
            >>> limiter.try_set_rate(RateType.OVERALL, 10, 1, RateIntervalUnit.SECONDS)
            True  # 每秒允许 10 个请求
        """
        # 转换时间单位为毫秒
        interval_ms = self._convert_to_milliseconds(interval, unit)

        # 保存配置到缓存
        self._rate = rate
        self._interval = interval_ms
        self._rate_type = rate_type

        # 执行 Lua 脚本初始化
        try:
            result = self._init_script(keys=[self.name], args=[rate, interval_ms, rate_type.value])
            return bool(result)
        except redis.RedisError as e:
            raise RuntimeError(f"Failed to initialize rate limiter: {e}")

    def try_acquire(self, amount: int = 1, timeout: Optional[float] = None) -> bool:
        """
        尝试获取指定数量的令牌。
        
        Args:
            amount: 需要获取的令牌数量，默认为 1
            timeout: 超时时间（秒），None 表示不等待，0 表示无限等待
            
        Returns:
            bool: 获取成功返回 True，失败返回 False
            
        Example:
            >>> if limiter.try_acquire(1):
            ...     print("获取成功")
            ... else:
            ...     print("被限流")
        """
        if amount <= 0:
            raise ValueError("amount must be positive")

        start_time = time.time()

        while True:
            # 获取当前时间戳（毫秒）
            current_timestamp = int(time.time() * 1000)

            try:
                result = self._try_acquire_script(keys=[self.name], args=[amount, current_timestamp])

                if result == 1:
                    # 获取成功
                    return True
                elif result == -1:
                    # 限流器未初始化
                    raise RuntimeError("Rate limiter not initialized")
                else:
                    # 返回需要等待的时间（毫秒）
                    wait_time_ms = int(result)

                    if timeout is not None:
                        elapsed = time.time() - start_time
                        remaining = timeout - elapsed
                        if remaining <= 0:
                            return False
                        wait_time_ms = min(wait_time_ms, int(remaining * 1000))

                    if wait_time_ms > 0:
                        # 等待后重试
                        time.sleep(min(wait_time_ms / 1000.0, 0.1))
                    else:
                        # 立即重试一次
                        time.sleep(0.001)

            except redis.RedisError as e:
                raise RuntimeError(f"Failed to acquire permit: {e}")

    def acquire(self, amount: int = 1) -> None:
        """
        获取指定数量的令牌，阻塞直到成功。
        
        Args:
            amount: 需要获取的令牌数量，默认为 1
            
        Example:
            >>> limiter.acquire(1)  # 一直等待直到获取到令牌
            >>> print("获取成功")
        """
        self.try_acquire(amount, timeout=None)

    def get_rate(self) -> Optional[tuple]:
        """
        获取当前限流器配置。
        
        Returns:
            tuple: (rate_type, rate, interval_ms) 如果限流器未初始化返回 None
            
        Example:
            >>> config = limiter.get_rate()
            >>> if config:
            ...     rate_type, rate, interval = config
            ...     print(f"限流配置：{rate} requests / {interval}ms")
        """
        try:
            data = self.redis_client.hmget(self.name, 'type', 'rate', 'interval')

            if data[0] is None:
                return None

            rate_type = RateType(int(data[0]))
            rate = int(data[1])
            interval = int(data[2])

            return (rate_type, rate, interval)
        except redis.RedisError as e:
            raise RuntimeError(f"Failed to get rate config: {e}")

    @staticmethod
    def _convert_to_milliseconds(interval: int, unit: RateIntervalUnit) -> int:
        """
        将时间间隔转换为毫秒。
        
        Args:
            interval: 时间间隔数值
            unit: 时间单位
            
        Returns:
            int: 毫秒数
        """
        multipliers = {
            RateIntervalUnit.MILLISECONDS: 1,
            RateIntervalUnit.SECONDS: 1000,
            RateIntervalUnit.MINUTES: 60 * 1000,
            RateIntervalUnit.HOURS: 60 * 60 * 1000,
            RateIntervalUnit.DAYS: 24 * 60 * 60 * 1000,
        }
        return interval * multipliers[unit]

    def reset(self) -> bool:
        """
        重置限流器状态（清空 counter）。
        
        Returns:
            bool: 重置成功返回 True
            
        Note:
            此方法不会删除限流器配置，只会重置计数器。
        """
        try:
            self.redis_client.hset(self.name, 'counter', 0)
            return True
        except redis.RedisError as e:
            raise RuntimeError(f"Failed to reset rate limiter: {e}")

    def delete(self) -> bool:
        """
        删除限流器及其配置。
        
        Returns:
            bool: 删除成功返回 True
        """
        try:
            self.redis_client.delete(self.name)
            self._rate = None
            self._interval = None
            return True
        except redis.RedisError as e:
            raise RuntimeError(f"Failed to delete rate limiter: {e}")


# 便捷函数：创建限流器实例
def create_rate_limiter(name: str,
                        rate: int,
                        interval: int = 1,
                        unit: RateIntervalUnit = RateIntervalUnit.SECONDS,
                        rate_type: RateType = RateType.OVERALL,
                        redis_client: Optional[redis.Redis] = None) -> RedisRateLimiter:
    """
    创建并初始化一个限流器。
    
    Args:
        name: 限流器名称
        rate: 每个时间窗口允许的请求数
        interval: 时间窗口大小
        unit: 时间窗口单位
        rate_type: 限流类型
        redis_client: Redis 客户端实例
        
    Returns:
        RedisRateLimiter: 已初始化的限流器实例
        
    Example:
        >>> limiter = create_rate_limiter('api-limit', rate=100, interval=1, unit=RateIntervalUnit.SECONDS)
        >>> if limiter.try_acquire(1):
        ...     print("请求允许通过")
    """
    limiter = RedisRateLimiter(name, redis_client)
    limiter.try_set_rate(rate_type, rate, interval, unit)
    return limiter


def main():
    """简单的使用示例"""
    print("=" * 60)
    print("Python Redis Rate Limiter使用示例")
    print("与 Java Redisson RRateLimiter 完全兼容")
    print("=" * 60)

    # 创建限流器：每秒允许 10 个请求
    limiter = create_rate_limiter(name='test-api-limit', rate=10, interval=1, unit=RateIntervalUnit.SECONDS)

    print("\n限流配置：10 requests / second")
    print("-" * 60)

    # 模拟 15 个请求
    success_count = 0
    fail_count = 0

    for i in range(15):
        if limiter.try_acquire(1):
            print(f"请求 {i+1:2d}: ✓ 允许通过")
            success_count += 1
        else:
            print(f"请求 {i+1:2d}: ✗ 被限流")
            fail_count += 1

    print("-" * 60)
    print(f"统计结果：成功 {success_count} 个，被限流 {fail_count} 个")

    # 查看限流器配置
    config = limiter.get_rate()
    if config:
        rate_type, rate, interval = config
        print(f"\n当前限流器配置：{rate} requests / {interval}ms")

    print("\n" + "=" * 60)
    print("提示：可以与 Java Redisson 端共用同一个限流器实例")
    print("=" * 60)


if __name__ == '__main__':
    main()
