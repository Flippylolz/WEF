import createClient from "openapi-fetch";

import type { components, paths } from "@/generated/api";

export type EstateResponse = components["schemas"]["EstateResponse"];

export type EstatesRequestResult =
  { state: "ready"; items: EstateResponse[] } | { state: "error" };

type Fetcher = (request: Request) => Promise<Response>;

const LOCAL_API_URL = "http://127.0.0.1:8000";

function getApiUrl() {
  return process.env.WEF_API_URL?.trim() || LOCAL_API_URL;
}

export async function fetchEstates(
  fetcher?: Fetcher,
): Promise<EstatesRequestResult> {
  const client = createClient<paths>({
    baseUrl: getApiUrl(),
    ...(fetcher ? { fetch: fetcher } : {}),
  });

  try {
    const { data, error, response } = await client.GET("/api/v1/estates", {
      cache: "no-store",
    });

    if (!response.ok || error !== undefined || data === undefined) {
      return { state: "error" };
    }

    return { state: "ready", items: data.items };
  } catch {
    return { state: "error" };
  }
}
