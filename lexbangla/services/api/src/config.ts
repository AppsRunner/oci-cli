export const config = {
  port: Number(process.env.API_PORT ?? 3000),
  host: process.env.API_HOST ?? '0.0.0.0',
  minio: {
    endPoint: process.env.MINIO_ENDPOINT ?? 'localhost',
    port: Number(process.env.MINIO_PORT ?? 9000),
    useSSL: process.env.MINIO_USE_SSL === 'true',
    accessKey: process.env.MINIO_ACCESS_KEY ?? 'minioadmin',
    secretKey: process.env.MINIO_SECRET_KEY ?? 'minioadmin',
  },
  minioBucket: process.env.MINIO_BUCKET ?? 'lexbangla-documents',
  redis: {
    host: process.env.REDIS_HOST ?? 'localhost',
    port: Number(process.env.REDIS_PORT ?? 6379),
  },
};
