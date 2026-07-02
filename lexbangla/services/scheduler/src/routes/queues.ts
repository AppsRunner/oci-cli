import type { FastifyInstance } from 'fastify';
import type { QueueManager } from '../queue-manager';

export async function queueRoutes(app: FastifyInstance, manager: QueueManager): Promise<void> {
  app.get('/queues', async (_req, reply) => {
    reply.send(await manager.getAllStats());
  });

  app.get<{ Params: { name: string } }>('/queues/:name', async (req, reply) => {
    try {
      reply.send(await manager.getStats(req.params.name));
    } catch {
      reply.code(404).send({ error: `Queue not found: ${req.params.name}` });
    }
  });
}
