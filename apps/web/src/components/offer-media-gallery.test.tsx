import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OfferMediaGallery } from "@/components/offer-media-gallery";
import type { OfferDetail } from "@/lib/catalog-api";

vi.mock("next-intl", () => ({
  useTranslations:
    () => (key: string, values?: Record<string, string | number>) => {
      if (values) return `${key}:${JSON.stringify(values)}`;
      return key;
    },
}));

const detail: Pick<OfferDetail, "display_name" | "location"> = {
  display_name: "unit · secondary",
  location: {
    id: "10000000-0000-4000-8000-000000000001",
    display_name: "Synthetic Central Residence",
    display_address: "Synthetic address, Warsaw",
    district: "srodmiescie",
    coordinate_precision: "building",
    confidence: "high",
  },
};

function media(
  overrides: Partial<OfferDetail["media"][number]> & { media_asset_id: string },
): OfferDetail["media"][number] {
  return {
    position: 0,
    media_type: "image",
    mime_type: "image/jpeg",
    thumbnail_url: "/media/thumb.jpg",
    content_url: "/media/full.jpg",
    ...overrides,
  };
}

describe("OfferMediaGallery", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows an empty state when the offer has no media", () => {
    render(<OfferMediaGallery detail={detail} media={[]} />);
    expect(screen.getByText("detailNoMedia")).toBeInTheDocument();
  });

  it("opens an image lightbox and closes it from the toolbar", async () => {
    const user = userEvent.setup();
    render(
      <OfferMediaGallery
        detail={detail}
        media={[
          media({ media_asset_id: "image-1" }),
          media({
            media_asset_id: "video-1",
            media_type: "video",
            mime_type: "video/mp4",
            thumbnail_url: null,
            content_url: "/media/clip.mp4",
          }),
          media({
            media_asset_id: "missing-1",
            thumbnail_url: null,
            content_url: null,
          }),
        ]}
      />,
    );

    expect(screen.getByText("detailVideoBadge")).toBeInTheDocument();
    expect(screen.getByLabelText(/media 3 of 3/)).toHaveTextContent(
      "detailMissingMedia",
    );

    await user.click(
      screen.getByRole("button", {
        name: 'detailOpenMedia:{"index":1}',
      }),
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      within(screen.getByRole("dialog")).getByRole("img", {
        name: /media 1 of 3/,
      }),
    ).toHaveAttribute("src", "/media/full.jpg");

    await user.click(screen.getByRole("button", { name: "detailMediaNext" }));
    expect(screen.getByLabelText(/media 2 of 3/).tagName).toBe("VIDEO");

    await user.click(screen.getByRole("button", { name: "detailClose" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("navigates the lightbox with keyboard shortcuts", async () => {
    const user = userEvent.setup();
    render(
      <OfferMediaGallery
        detail={detail}
        media={[
          media({ media_asset_id: "image-1" }),
          media({
            media_asset_id: "image-2",
            content_url: "/media/second.jpg",
          }),
        ]}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: 'detailOpenMedia:{"index":1}',
      }),
    );
    await user.keyboard("{ArrowRight}");
    expect(
      within(screen.getByRole("dialog")).getByRole("img", {
        name: /media 2 of 2/,
      }),
    ).toHaveAttribute("src", "/media/second.jpg");
    await user.keyboard("{ArrowLeft}");
    expect(
      within(screen.getByRole("dialog")).getByRole("img", {
        name: /media 1 of 2/,
      }),
    ).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows a missing-media slide when keyboard navigation reaches an item without a URL", async () => {
    const user = userEvent.setup();
    render(
      <OfferMediaGallery
        detail={detail}
        media={[
          media({ media_asset_id: "image-1" }),
          media({
            media_asset_id: "missing-1",
            thumbnail_url: null,
            content_url: null,
          }),
        ]}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: 'detailOpenMedia:{"index":1}',
      }),
    );
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("dialog")).toHaveTextContent("detailMissingMedia");
  });
});
