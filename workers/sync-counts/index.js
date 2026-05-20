import { DynamoDBClient, GetItemCommand } from "@aws-sdk/client-dynamodb";

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

    const res = await client.send(new GetItemCommand({
      TableName: env.DYNAMODB_TABLE,
      Key: {
        PK: { S: "APP#STATS" },
        SK: { S: "LEAGUE_COUNT" },
      },
    }));

    const count = parseInt(res.Item?.league_count?.N ?? "0");
    await env.COUNTS_KV.put("leagueCount", String(count));

    console.log(`Synced league count: ${count}`);
  }
};