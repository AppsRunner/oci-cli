import { Client } from 'minio';
import type { Readable } from 'stream';

export interface MinioConfig {
  endPoint: string;
  port: number;
  useSSL: boolean;
  accessKey: string;
  secretKey: string;
}

export class MinioStorageService {
  private readonly client: Client;

  constructor(config: MinioConfig) {
    this.client = new Client(config);
  }

  async ensureBucket(bucket: string): Promise<void> {
    const exists = await this.client.bucketExists(bucket);
    if (!exists) {
      await this.client.makeBucket(bucket);
    }
  }

  async putObject(
    bucket: string,
    key: string,
    data: Buffer | Readable,
    size: number,
    contentType: string,
  ): Promise<void> {
    await this.client.putObject(bucket, key, data, size, {
      'Content-Type': contentType,
    });
  }

  async getObject(bucket: string, key: string): Promise<Buffer> {
    const stream = await this.client.getObject(bucket, key);
    return streamToBuffer(stream);
  }

  async removeObject(bucket: string, key: string): Promise<void> {
    await this.client.removeObject(bucket, key);
  }

  async presignedGetUrl(bucket: string, key: string, expirySeconds = 3600): Promise<string> {
    return this.client.presignedGetObject(bucket, key, expirySeconds);
  }
}

function streamToBuffer(stream: Readable): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    stream.on('data', (chunk: unknown) =>
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk as string)),
    );
    stream.on('end', () => resolve(Buffer.concat(chunks)));
    stream.on('error', reject);
  });
}
