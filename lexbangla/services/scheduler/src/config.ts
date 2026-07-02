export const config = {
  redis: {
    host: process.env.REDIS_HOST ?? 'localhost',
    port: Number(process.env.REDIS_PORT ?? 6379),
  },
  server: {
    host: process.env.SCHEDULER_HOST ?? '0.0.0.0',
    port: Number(process.env.SCHEDULER_PORT ?? 3001),
  },
  reingest: {
    cronPattern: process.env.REINGEST_CRON ?? '0 * * * *',
    defaultLanguage: process.env.DEFAULT_LANGUAGE ?? 'ben+eng',
    defaultSourceUrl: process.env.REINGEST_SOURCE_URL ?? '',
  },
};
