export const WORKER_HEALTH_KEY_PREFIX = 'worker:health:' as const;
export const WORKER_HEALTH_TTL_SECONDS = 30 as const;

export interface WorkerHealthReport {
  workerId: string;
  queueName: string;
  status: 'idle' | 'busy' | 'draining';
  concurrency: number;
  activeJobs: number;
  jobsProcessed: number;
  jobsFailed: number;
  uptimeSeconds: number;
  memoryMB: number;
  lastSeen: string;
}
