import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const send = vi.fn();
const clientCtor = vi.fn();

vi.mock('@aws-sdk/client-dynamodb', () => ({
  DynamoDBClient: class {
    constructor(config) {
      clientCtor(config);
      this.send = send;
    }
  },
  // Echo the input so assertions can inspect exactly what would be sent.
  QueryCommand: class {
    constructor(input) {
      this.input = input;
    }
  },
}));

const { default: worker } = await import('./index.js');

function makeEnv(overrides = {}) {
  return {
    AWS_ACCESS_KEY_ID: 'AKIA',
    AWS_SECRET_ACCESS_KEY: 'secret',
    AWS_REGION: 'us-east-1',
    DYNAMODB_TABLE: 'leagueql-table',
    COUNTS_KV: { put: vi.fn(async () => {}) },
    ...overrides,
  };
}

beforeEach(() => {
  send.mockReset();
  clientCtor.mockReset();
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('fetch', () => {
  it('is not publicly routable', async () => {
    const res = await worker.fetch();
    expect(res.status).toBe(404);
  });
});

describe('scheduled: credentials guard', () => {
  it.each([
    ['access key missing', { AWS_ACCESS_KEY_ID: undefined }],
    ['access key blank', { AWS_ACCESS_KEY_ID: '   ' }],
    ['secret missing', { AWS_SECRET_ACCESS_KEY: undefined }],
    ['secret blank', { AWS_SECRET_ACCESS_KEY: '' }],
  ])('skips DynamoDB and KV when %s', async (_label, overrides) => {
    const env = makeEnv(overrides);
    await worker.scheduled({}, env, {});
    expect(clientCtor).not.toHaveBeenCalled();
    expect(send).not.toHaveBeenCalled();
    expect(env.COUNTS_KV.put).not.toHaveBeenCalled();
    expect(console.error).toHaveBeenCalledWith(
      'Missing or empty AWS credentials',
    );
  });
});

describe('scheduled: counting', () => {
  it('queries the sparse GSI3 METADATA partition with Select=COUNT', async () => {
    send.mockResolvedValueOnce({ Count: 7 });
    await worker.scheduled({}, makeEnv(), {});
    const { input } = send.mock.calls[0][0];
    expect(input).toMatchObject({
      TableName: 'leagueql-table',
      IndexName: 'GSI3',
      KeyConditionExpression: 'SK = :sk',
      ExpressionAttributeValues: { ':sk': { S: 'METADATA' } },
      Select: 'COUNT',
    });
  });

  it('builds the client from the worker env', async () => {
    send.mockResolvedValueOnce({ Count: 1 });
    await worker.scheduled({}, makeEnv(), {});
    expect(clientCtor).toHaveBeenCalledWith({
      region: 'us-east-1',
      credentials: { accessKeyId: 'AKIA', secretAccessKey: 'secret' },
    });
  });

  it('stores the count as a string under leagueCount', async () => {
    send.mockResolvedValueOnce({ Count: 123 });
    const env = makeEnv();
    await worker.scheduled({}, env, {});
    expect(env.COUNTS_KV.put).toHaveBeenCalledWith('leagueCount', '123');
  });

  it('sums Count across every page via LastEvaluatedKey', async () => {
    send
      .mockResolvedValueOnce({ Count: 10, LastEvaluatedKey: { PK: { S: 'a' } } })
      .mockResolvedValueOnce({ Count: 20, LastEvaluatedKey: { PK: { S: 'b' } } })
      .mockResolvedValueOnce({ Count: 5 });
    const env = makeEnv();
    await worker.scheduled({}, env, {});

    expect(send).toHaveBeenCalledTimes(3);
    expect(send.mock.calls[0][0].input.ExclusiveStartKey).toBeUndefined();
    expect(send.mock.calls[1][0].input.ExclusiveStartKey).toEqual({
      PK: { S: 'a' },
    });
    expect(send.mock.calls[2][0].input.ExclusiveStartKey).toEqual({
      PK: { S: 'b' },
    });
    expect(env.COUNTS_KV.put).toHaveBeenCalledWith('leagueCount', '35');
  });

  it('writes 0 for an empty index (Count omitted)', async () => {
    send.mockResolvedValueOnce({});
    const env = makeEnv();
    await worker.scheduled({}, env, {});
    expect(env.COUNTS_KV.put).toHaveBeenCalledWith('leagueCount', '0');
  });

  it('is idempotent: re-running with the same data writes the same value', async () => {
    send.mockResolvedValue({ Count: 9 });
    const env = makeEnv();
    await worker.scheduled({}, env, {});
    await worker.scheduled({}, env, {});
    expect(env.COUNTS_KV.put.mock.calls).toEqual([
      ['leagueCount', '9'],
      ['leagueCount', '9'],
    ]);
  });
});

describe('scheduled: failure handling', () => {
  it('leaves the previous KV value untouched when DynamoDB fails', async () => {
    send.mockRejectedValueOnce(new Error('AccessDenied'));
    const env = makeEnv();
    await expect(worker.scheduled({}, env, {})).resolves.toBeUndefined();
    expect(env.COUNTS_KV.put).not.toHaveBeenCalled();
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('Failed to sync league count'),
    );
  });

  it('does not write a partial count when a later page fails', async () => {
    send
      .mockResolvedValueOnce({ Count: 10, LastEvaluatedKey: { PK: { S: 'a' } } })
      .mockRejectedValueOnce(new Error('Throttled'));
    const env = makeEnv();
    await worker.scheduled({}, env, {});
    expect(env.COUNTS_KV.put).not.toHaveBeenCalled();
  });

  it('logs and swallows a KV write failure', async () => {
    send.mockResolvedValueOnce({ Count: 3 });
    const env = makeEnv({
      COUNTS_KV: { put: vi.fn(async () => { throw new Error('kv down'); }) },
    });
    await expect(worker.scheduled({}, env, {})).resolves.toBeUndefined();
    expect(console.error).toHaveBeenCalledWith(
      expect.stringContaining('kv down'),
    );
  });
});
