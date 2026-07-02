import type { FastifyInstance } from 'fastify';
import type { ReingestionScheduler } from '../scheduler';

interface CreateScheduleBody {
  name: string;
  cron: string;
  sourceUrl: string;
  language?: string;
}

export async function scheduleRoutes(
  app: FastifyInstance,
  scheduler: ReingestionScheduler,
): Promise<void> {
  app.get('/schedules', async (_req, reply) => {
    reply.send(await scheduler.list());
  });

  app.post<{ Body: CreateScheduleBody }>('/schedules', async (req, reply) => {
    const { name, cron, sourceUrl, language } = req.body;
    if (!name || !cron || !sourceUrl) {
      return reply.code(400).send({ error: 'name, cron, and sourceUrl are required' });
    }
    const entry = await scheduler.add({ name, cron, sourceUrl, language });
    reply.code(201).send(entry);
  });

  app.delete<{ Params: { key: string } }>('/schedules/:key', async (req, reply) => {
    const removed = await scheduler.remove(req.params.key);
    if (!removed) return reply.code(404).send({ error: 'Schedule not found' });
    reply.code(204).send();
  });
}
