import { useQuery } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { QueryProvider } from "@/components/query-provider";

function Probe() {
  const query = useQuery({
    queryKey: ["probe"],
    queryFn: async () => "ready",
  });
  return <p>{query.data ?? "pending"}</p>;
}

describe("QueryProvider", () => {
  it("exposes a query client to descendants", async () => {
    render(
      <QueryProvider>
        <Probe />
      </QueryProvider>,
    );
    expect(screen.getByText("pending")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("ready")).toBeInTheDocument());
  });
});
