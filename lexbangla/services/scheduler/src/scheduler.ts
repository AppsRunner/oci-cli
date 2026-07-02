import type { Queue } from 'bullmq';
import type { IngestJobData } from '@lexbangla/core';
import { REINGEST_QUEUE_NAME } from '@lexbangla/core';
import type { QueueManager } from './queue-manager';

export interface ScheduleEntry {
  key: string;
  name: string;
  cron: string;
  nextRun: number;
}

export interface CreateScheduleOptions {
  name: string;
  cron: string;
  sourceUrl: string;
  language?: string;
}

export class ReingestionScheduler {
  private readonly queue: Queue<IngestJobData>;

  constructor(manager: QueueManager) {
    this.queue = manager.get(REINGEST_QUEUE_NAME) as Queue<IngestJobData>;
  }

  async add(opts: CreateScheduleOptions): Promise<ScheduleEntry> {
    const { name, cron, sourceUrl, language = 'ben+eng' } = opts;

    await this.queue.add(
      name,
      { sourceUrl, sourceType: 'url', language, triggeredBy: 'scheduled', scheduleKey: name },
      { repeat: { pattern: cron } },
    );

    const jobs = await this.queue.getRepeatableJobs();
    const created = jobs.find((j) => j.name === name);

    return { key: created?.key ?? name, name, cron, nextRun: created?.next ?? 0 };
  }

  async remove(key: string): Promise<boolean> {
    const jobs = await this.queue.getRepeatableJobs();
    const target = jobs.find((j) => j.name === key || j.key === key);
    if (!target) return false;
    await this.queue.removeRepeatableByKey(target.key);
    return true;
  }

  async list(): Promise<ScheduleEntry[]> {
    const jobs = await this.queue.getRepeatableJobs();
    return jobs.map((j) => ({
      key: j.key,
      name: j.name,
      cron: j.pattern ?? '',
      nextRun: j.next,
    }));
  }
}
