import { Redis } from 'ioredis';
import type { Worker } from 'bullmq';
import type { WorkerHealthReport } from '@lexbangla/core';
import { WORKER_HEALTH_KEY_PREFIX, WORKER_HEALTH_TTL_SECONDS } from '@lexbangla/core';
import { randomUUID } from 'crypto';

export class WorkerHealthMonitor {
  private readonly workerId = randomUUID();
  private readonly startedAt = Date.now();
  private jobsProcessed = 0;
  private jobsFailed = 0;
  private activeJobs = 0;
  private intervalId?: ReturnType<typeof setInterval>;
  private readonly redis: Redis;

  constructor(
    private readonly worker: Worker,
    private readonly queueName: string,
    redisHost: string,
    redisPort: number,
    private readonly concurrency: number = 1,
    private readonly reportIntervalMs = 10_000,
  ) {
    this.redis = new Redis({ host: redisHost, port: redisPort, lazyConnect: true });
  }

  async start(): Promise<void> {
    await this.redis.connect();

    this.worker.on('active', () => {
      this.activeJobs++;
    });
    this.worker.on('completed', () => {
      this.activeJobs = Math.max(0, this.activeJobs - 1);
      this.jobsProcessed++;
    });
    this.worker.on('failed', () => {
      this.activeJobs = Math.max(0, this.activeJobs - 1);
      this.jobsFailed++;
    });

    this.intervalId = setInterval(() => {
      this.report().catch(console.error);
    }, this.reportIntervalMs);

    await this.report();
    console.log(`[health] Worker ${this.workerId} reporting to Redis every ${this.reportIntervalMs}ms`);
  }

  private async report(): Promise<void> {
    const report: WorkerHealthReport = {
      workerId: this.workerId,
      queueName: this.queueName,
      status: this.activeJobs > 0 ? 'busy' : 'idle',
      concurrency: this.concurrency,
      activeJobs: this.activeJobs,
      jobsProcessed: this.jobsProcessed,
      jobsFailed: this.jobsFailed,
      uptimeSeconds: Math.floor((Date.now() - this.startedAt) / 1000),
      memoryMB: Math.round(process.memoryUsage().rss / 1024 / 1024),
      lastSeen: new Date().toISOString(),
    };

    const key = `${WORKER_HEALTH_KEY_PREFIX}${this.workerId}`;
    await this.redis.setex(key, WORKER_HEALTH_TTL_SECONDS, JSON.stringify(report));
  }

  async stop(): Promise<void> {
    if (this.intervalId) clearInterval(this.intervalId);
    await this.redis.quit();
  }
}
