import type { FastifyInstance } from 'fastify';
import type { WorkerRegistry } from '../worker-registry';

export async function workerRoutes(
  app: FastifyInstance,
  registry: WorkerRegistry,
): Promise<void> {
  app.get('/workers', async (_req, reply) => {
    reply.send(await registry.getAll());
  });

  app.get<{ Params: { id: string } }>('/workers/:id', async (req, reply) => {
    const report = await registry.get(req.params.id);
    if (!report) return reply.code(404).send({ error: 'Worker not found' });
    reply.send(report);
  });
}
