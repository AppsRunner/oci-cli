import { Redis } from 'ioredis';
import type { WorkerHealthReport } from '@lexbangla/core';
import { WORKER_HEALTH_KEY_PREFIX } from '@lexbangla/core';

export class WorkerRegistry {
  constructor(private readonly redis: Redis) {}

  async getAll(): Promise<WorkerHealthReport[]> {
    const keys = await this.redis.keys(`${WORKER_HEALTH_KEY_PREFIX}*`);
    if (keys.length === 0) return [];
    const values = await this.redis.mget(...keys);
    return values
      .filter((v): v is string => v !== null)
      .map((v) => JSON.parse(v) as WorkerHealthReport);
  }

  async get(workerId: string): Promise<WorkerHealthReport | null> {
    const raw = await this.redis.get(`${WORKER_HEALTH_KEY_PREFIX}${workerId}`);
    return raw ? (JSON.parse(raw) as WorkerHealthReport) : null;
  }
}
