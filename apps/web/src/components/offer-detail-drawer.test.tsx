import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OfferDetailDrawer } from "@/components/offer-detail-drawer";
import type { Account } from "@/lib/auth-api";
import type { OfferDetail } from "@/lib/catalog-api";
import * as catalogApi from "@/lib/catalog-api";
import * as contactsApi from "@/lib/contacts-api";

vi.mock("next-intl", () => ({
  useTranslations:
    () => (key: string, values?: Record<string, string | number>) => {
      if (values) {
        return `${key}:${JSON.stringify(values)}`;
      }
      return key;
    },
}));

vi.mock("@/lib/contacts-api", () => ({
  revealOfferContacts: vi.fn(),
}));

const detail: OfferDetail = {
  id: "20000000-0000-4000-8000-000000000001",
  content_type: "development",
  market_type: "primary",
  display_name: "development · primary",
  data_confidence: "complete",
  data_origin: "parser",
  published_at: "2026-08-01T10:00:00Z",
  currency: "PLN",
  price_min_minor: 80_000_000,
  price_max_minor: 125_000_000,
  parking_price_min_minor: 4_500_000,
  parking_price_max_minor: 4_500_000,
  parking_included_in_price: false,
  storage_price_min_minor: null,
  storage_price_max_minor: null,
  storage_included_in_price: true,
  area_min_sqm: "35.00",
  area_max_sqm: "71.50",
  rooms_min: 1,
  rooms_max: 3,
  floor_label: null,
  delivery_label: "Synthetic delivery",
  public_source_text: "Masked public text only.",
  parser_version: "synthetic-m1-v1",
  location: {
    id: "10000000-0000-4000-8000-000000000001",
    display_name: "Synthetic Central Residence",
    display_address: "Synthetic address, Warsaw",
    district: "srodmiescie",
    coordinate_precision: "district",
    confidence: "low",
  },
  development: {
    id: "30000000-0000-4000-8000-000000000001",
    display_name: "Synthetic Project",
    name_confidence: "medium",
  },
  field_confidence: [{ field: "area_sqm", confidence: "high" }],
  media: [
    {
      media_asset_id: "40000000-0000-4000-8000-000000000001",
      position: 0,
      media_type: "image",
      mime_type: "image/jpeg",
      thumbnail_url: "/media/thumb.jpg",
      content_url: "/media/full.jpg",
    },
  ],
  source_message_id: "50000000-0000-4000-8000-000000000001",
  verified_source_url: "https://t.me/elestate_warszawa/42",
  source_history: [
    {
      source_message_id: "50000000-0000-4000-8000-000000000001",
      relationship: "original",
      published_at: "2026-08-01T10:00:00Z",
      edited_at: null,
    },
  ],
};

const signedInAccount: Account = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "warsaw",
  role: "user",
  must_change_password: false,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

class OfferNotFoundError extends Error {
  override name = "OfferNotFoundError";
}

function DrawerHarness({
  offerId,
  matchesFilters = true,
  account = null,
  onClose = () => undefined,
  onRequestSignIn = () => undefined,
  onRequestPasswordChange = () => undefined,
}: {
  offerId: string;
  matchesFilters?: boolean;
  account?: Account | null;
  onClose?: () => void;
  onRequestSignIn?: () => void;
  onRequestPasswordChange?: () => void;
}) {
  const returnFocusRef = { current: document.createElement("button") };
  const detailQuery = useQuery({
    queryKey: ["offer-detail", offerId],
    queryFn: async ({ signal }) => {
      const result = await catalogApi.fetchOfferDetail(offerId, { signal });
      if (result.state === "not_found") throw new OfferNotFoundError();
      if (result.state === "error") throw new Error("offer-detail");
      return result.data;
    },
  });

  return (
    <OfferDetailDrawer
      open
      offerId={offerId}
      matchesFilters={matchesFilters}
      detailQuery={detailQuery}
      account={account}
      onClose={onClose}
      onRequestSignIn={onRequestSignIn}
      onRequestPasswordChange={onRequestPasswordChange}
      returnFocusRef={returnFocusRef}
    />
  );
}

function renderDrawer(
  offerId = detail.id,
  options: {
    account?: Account | null;
    onRequestSignIn?: () => void;
    onRequestPasswordChange?: () => void;
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DrawerHarness offerId={offerId} {...options} />
    </QueryClientProvider>,
  );
}

describe("OfferDetailDrawer", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders masked detail fields and verified Telegram link", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer();

    expect(
      await screen.findByText("development · primary"),
    ).toBeInTheDocument();
    expect(screen.getByText("Masked public text only.")).toBeInTheDocument();
    expect(
      screen.getByText("detailAvailabilityDisclaimer"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "detailOpenTelegram" }),
    ).toHaveAttribute("href", "https://t.me/elestate_warszawa/42");
    expect(
      screen.getByRole("link", { name: "detailOpenTelegram" }),
    ).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows non-link fallback when verified url is absent", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: { ...detail, verified_source_url: null },
    });
    renderDrawer();

    expect(
      await screen.findByText(/detailSourceFallbackWithId/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "detailOpenTelegram" }),
    ).not.toBeInTheDocument();
  });

  it("announces not-found without leaking payloads", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "not_found",
    });
    renderDrawer();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "detailNotFound",
    );
  });

  it("asks anonymous users to sign in instead of revealing", async () => {
    const onRequestSignIn = vi.fn();
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer(detail.id, { onRequestSignIn });

    expect(
      await screen.findByText("detailRevealSignInRequired"),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealSignInAction" }),
    );
    expect(onRequestSignIn).toHaveBeenCalled();
    expect(contactsApi.revealOfferContacts).not.toHaveBeenCalled();
  });

  it("blocks reveal until forced password change completes", async () => {
    const onRequestPasswordChange = vi.fn();
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    renderDrawer(detail.id, {
      account: { ...signedInAccount, must_change_password: true },
      onRequestPasswordChange,
    });

    expect(
      await screen.findByText("detailRevealPasswordRequired"),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealPasswordAction" }),
    );
    expect(onRequestPasswordChange).toHaveBeenCalled();
    expect(contactsApi.revealOfferContacts).not.toHaveBeenCalled();
  });

  it("reveals contacts only after an explicit click", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    vi.mocked(contactsApi.revealOfferContacts).mockResolvedValue({
      state: "ready",
      data: {
        contacts: [
          {
            kind: "phone",
            value: "+48111222333",
            masked_value: "+48***333",
          },
        ],
      },
    });
    renderDrawer(detail.id, { account: signedInAccount });

    expect(
      await screen.findByRole("button", { name: "detailRevealContacts" }),
    ).toBeInTheDocument();
    expect(contactsApi.revealOfferContacts).not.toHaveBeenCalled();
    expect(screen.queryByText("+48111222333")).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );

    expect(await screen.findByText("+48111222333")).toBeInTheDocument();
    expect(contactsApi.revealOfferContacts).toHaveBeenCalledWith(detail.id);
  });

  it("shows rate-limit and unavailable errors from reveal", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    vi.mocked(contactsApi.revealOfferContacts)
      .mockResolvedValueOnce({
        state: "error",
        code: "rate_limited",
      })
      .mockResolvedValueOnce({
        state: "error",
        code: "unavailable",
      })
      .mockResolvedValueOnce({
        state: "error",
        code: "forbidden",
      })
      .mockResolvedValueOnce({
        state: "error",
      });
    renderDrawer(detail.id, { account: signedInAccount });

    const reveal = await screen.findByRole("button", {
      name: "detailRevealContacts",
    });
    await userEvent.click(reveal);
    expect(
      await screen.findByText("detailRevealError.rate_limited"),
    ).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(
      await screen.findByText("detailRevealError.unavailable"),
    ).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(
      await screen.findByText("detailRevealError.forbidden"),
    ).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(
      await screen.findByText("detailRevealError.unknown"),
    ).toBeInTheDocument();
  });

  it("closes from escape and restores focus to the trigger", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: detail,
    });
    const trigger = document.createElement("button");
    document.body.append(trigger);
    trigger.focus();

    function ClosableDrawer() {
      const [open, setOpen] = useState(true);
      return (
        <OfferDetailDrawer
          open={open}
          offerId={detail.id}
          matchesFilters={false}
          detailQuery={
            {
              data: detail,
              error: null,
              isError: false,
              isPending: false,
              isSuccess: true,
            } as never
          }
          account={null}
          onClose={() => setOpen(false)}
          onRequestSignIn={() => undefined}
          onRequestPasswordChange={() => undefined}
          returnFocusRef={{ current: trigger }}
        />
      );
    }

    render(<ClosableDrawer />);
    await userEvent.keyboard("{Escape}");
    await waitFor(() =>
      expect(
        screen.queryByTestId("offer-detail-overlay"),
      ).not.toBeInTheDocument(),
    );
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("shows empty revealed contacts and a date-only source fallback", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: {
        ...detail,
        verified_source_url: null,
        source_message_id: null,
        source_history: [
          {
            source_message_id: "50000000-0000-4000-8000-000000000002",
            relationship: "edit",
            published_at: "2026-08-01T10:00:00Z",
            edited_at: "2026-08-02T10:00:00Z",
          },
        ],
      },
    });
    vi.mocked(contactsApi.revealOfferContacts).mockResolvedValue({
      state: "ready",
      data: { contacts: [] },
    });
    renderDrawer(detail.id, { account: signedInAccount });

    expect(
      await screen.findByText(/detailSourceFallback:/),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "detailRevealContacts" }),
    );
    expect(await screen.findByText("detailRevealEmpty")).toBeInTheDocument();
  });

  it("shows loading and error states for the detail query", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const pending = render(
      <QueryClientProvider client={queryClient}>
        <OfferDetailDrawer
          open
          offerId={detail.id}
          matchesFilters
          detailQuery={
            {
              data: undefined,
              error: null,
              isError: false,
              isPending: true,
              isSuccess: false,
            } as never
          }
          account={null}
          onClose={() => undefined}
          onRequestSignIn={() => undefined}
          onRequestPasswordChange={() => undefined}
          returnFocusRef={{ current: document.createElement("button") }}
        />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("detailLoading");
    pending.unmount();

    render(
      <QueryClientProvider client={queryClient}>
        <OfferDetailDrawer
          open
          offerId={detail.id}
          matchesFilters
          detailQuery={
            {
              data: undefined,
              error: new Error("boom"),
              isError: true,
              isPending: false,
              isSuccess: false,
            } as never
          }
          account={null}
          onClose={() => undefined}
          onRequestSignIn={() => undefined}
          onRequestPasswordChange={() => undefined}
          returnFocusRef={{ current: document.createElement("button") }}
        />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("detailError");
  });

  it("renders partial data, omitted prices, and unsafe source urls", async () => {
    vi.spyOn(catalogApi, "fetchOfferDetail").mockResolvedValue({
      state: "ready",
      data: {
        ...detail,
        data_confidence: "partial",
        price_min_minor: null,
        price_max_minor: null,
        parking_price_min_minor: null,
        parking_price_max_minor: null,
        parking_included_in_price: false,
        storage_included_in_price: false,
        area_min_sqm: null,
        area_max_sqm: null,
        rooms_min: null,
        rooms_max: null,
        verified_source_url: "http://example.test/offer",
      },
    });
    renderDrawer();

    expect(await screen.findByText("partialData")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "detailOpenTelegram" }),
    ).not.toBeInTheDocument();
  });
});
