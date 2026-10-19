"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ListingCard } from "@/components/listing-card";
import {
  fetchUnmappedListings,
  type MapLocationQuery,
} from "@/lib/catalog-api";

type Props = {
  query: MapLocationQuery;
  onOfferTrigger: (offerId: string, node: HTMLButtonElement | null) => void;
  onSelectOffer: (
    offerId: string,
    matches: boolean,
    trigger: HTMLButtonElement,
  ) => void;
  favoriteIds: Set<string>;
  signedIn: boolean;
  onToggleStar: (locationId: string) => void;
};

export function UnmappedListings({
  query,
  onOfferTrigger,
  onSelectOffer,
  favoriteIds,
  signedIn,
  onToggleStar,
}: Props) {
  const t = useTranslations("map");
  const result = useInfiniteQuery({
    queryKey: ["unmapped-listings", query],
    queryFn: async ({ pageParam, signal }) => {
      const response = await fetchUnmappedListings(
        { ...query, limit: 20, ...(pageParam ? { cursor: pageParam } : {}) },
        { signal },
      );
      if (response.state === "error") throw new Error("unmapped-listings");
      return response.data;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
  const items = result.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <details className="uncertain-listings">
      <summary>
        {t("uncertainTitle")}{" "}
        {result.isSuccess
          ? `(${result.data.pages[0]?.matching_count ?? 0})`
          : ""}
      </summary>
      <p>{t("uncertainScope")}</p>
      {result.isPending ? <p role="status">{t("loading")}</p> : null}
      {result.isError ? (
        <div role="alert">
          <p>{t("uncertainError")}</p>
          <button type="button" onClick={() => void result.refetch()}>
            {t("retry")}
          </button>
        </div>
      ) : null}
      {result.isSuccess ? (
        <p>
          {t("uncertainCount", {
            count: result.data.pages[0]?.matching_count ?? 0,
          })}
        </p>
      ) : null}
      {result.isSuccess && items.length === 0 ? (
        <p>{t("uncertainEmpty")}</p>
      ) : null}
      <ul className="location-list" aria-label={t("uncertainTitle")}>
        {items.map((listing) => (
          <ListingCard
            key={listing.id}
            onMount={onOfferTrigger}
            listing={listing}
            selected={false}
            highlighted={false}
            starred={favoriteIds.has(listing.location.id)}
            showStar={signedIn}
            onSelect={(item, trigger) => onSelectOffer(item.id, true, trigger)}
            onHighlight={() => {}}
            onToggleStar={onToggleStar}
          />
        ))}
      </ul>
      {result.hasNextPage ? (
        <button
          type="button"
          className="load-more"
          disabled={result.isFetchingNextPage}
          onClick={() => void result.fetchNextPage()}
        >
          {result.isFetchingNextPage ? t("loadingMore") : t("loadMore")}
        </button>
      ) : null}
    </details>
  );
}
