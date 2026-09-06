import { DynamoDBClient, QueryCommand } from "@aws-sdk/client-dynamodb";

export default {
  async fetch() {
    return new Response("Not found", { status: 404 });
  },

  async scheduled(event, env, ctx) {
    if (!env.AWS_ACCESS_KEY_ID?.trim() || !env.AWS_SECRET_ACCESS_KEY?.trim()) {
      console.error("Missing or empty AWS credentials");
      return;
    }

    const client = new DynamoDBClient({
      region: env.AWS_REGION,
      credentials: {
        accessKeyId: env.AWS_ACCESS_KEY_ID,
        secretAccessKey: env.AWS_SECRET_ACCESS_KEY,
      },
    });

    // Derive the league count from the METADATA items themselves rather than a
    // maintained counter: GSI3 is a sparse index whose HASH is SK, so a single
    // SK = "METADATA" query enumerates exactly the league metadata items (one per
    // league). Select=COUNT avoids transferring item bodies, but the query still
    // paginates at DynamoDB's 1 MB scanned-per-page limit, so sum Count across
    // every page via LastEvaluatedKey.
    try {
      let count = 0;
      let exclusiveStartKey;
      do {
        const res = await client.send(new QueryCommand({
          TableName: env.DYNAMODB_TABLE,
          IndexName: "GSI3",
          KeyConditionExpression: "SK = :sk",
          ExpressionAttributeValues: { ":sk": { S: "METADATA" } },
          Select: "COUNT",
          ExclusiveStartKey: exclusiveStartKey,
        }));
        count += res.Count ?? 0;
        exclusiveStartKey = res.LastEvaluatedKey;
      } while (exclusiveStartKey);

      await env.COUNTS_KV.put("leagueCount", String(count));

      console.log(`Synced league count: ${count}`);
    } catch (err) {
      // Leave the previously-synced KV value in place on failure (an IAM/DynamoDB
      // error should not clobber a good count) and surface the reason in the logs.
      console.error(`Failed to sync league count: ${err?.stack ?? err}`);
    }
  }
};
