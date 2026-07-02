import Fastify from 'fastify';
import { Redis } from 'ioredis';
import { config } from './config';
import { QueueManager } from './queue-manager';
import { ReingestionScheduler } from './scheduler';
import { WorkerRegistry } from './worker-registry';
import { healthRoutes } from './routes/health';
import { queueRoutes } from './routes/queues';
import { scheduleRoutes } from './routes/schedules';
import { workerRoutes } from './routes/workers';

async function main(): Promise<void> {
  const redis = new Redis({ host: config.redis.host, port: config.redis.port, lazyConnect: true });
  await redis.connect();

  const manager = new QueueManager(config.redis);
  const scheduler = new ReingestionScheduler(manager);
  const registry = new WorkerRegistry(redis);

  if (config.reingest.defaultSourceUrl) {
    try {
      await scheduler.add({
        name: 'default-reingest',
        cron: config.reingest.cronPattern,
        sourceUrl: config.reingest.defaultSourceUrl,
        language: config.reingest.defaultLanguage,
      });
      console.log(`[scheduler] Default re-ingestion registered (${config.reingest.cronPattern})`);
    } catch (err) {
      console.warn('[scheduler] Could not register default schedule:', (err as Error).message);
    }
  }

  const app = Fastify({ logger: { level: process.env.LOG_LEVEL ?? 'info' } });

  await healthRoutes(app);
  await queueRoutes(app, manager);
  await scheduleRoutes(app, scheduler);
  await workerRoutes(app, registry);

  await app.listen({ host: config.server.host, port: config.server.port });

  const shutdown = async (): Promise<void> => {
    await app.close();
    await manager.close();
    await redis.quit();
    process.exit(0);
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
