import { Queue } from 'bullmq';
import type { ConnectionOptions } from 'bullmq';
import { OCR_QUEUE_NAME, REINGEST_QUEUE_NAME } from '@lexbangla/core';

export interface QueueStats {
  name: string;
  waiting: number;
  active: number;
  completed: number;
  failed: number;
  delayed: number;
  paused: boolean;
}

export class QueueManager {
  private readonly queues = new Map<string, Queue>();

  constructor(private readonly connection: ConnectionOptions) {
    this.register(OCR_QUEUE_NAME);
    this.register(REINGEST_QUEUE_NAME);
  }

  private register(name: string): void {
    this.queues.set(name, new Queue(name, { connection: this.connection }));
  }

  get(name: string): Queue {
    const q = this.queues.get(name);
    if (!q) throw new Error(`Queue not registered: ${name}`);
    return q;
  }

  async getStats(name: string): Promise<QueueStats> {
    const q = this.get(name);
    const [waiting, active, completed, failed, delayed, paused] = await Promise.all([
      q.getWaitingCount(),
      q.getActiveCount(),
      q.getCompletedCount(),
      q.getFailedCount(),
      q.getDelayedCount(),
      q.isPaused(),
    ]);
    return { name, waiting, active, completed, failed, delayed, paused };
  }

  async getAllStats(): Promise<QueueStats[]> {
    return Promise.all([...this.queues.keys()].map((n) => this.getStats(n)));
  }

  async close(): Promise<void> {
    await Promise.all([...this.queues.values()].map((q) => q.close()));
  }
}
