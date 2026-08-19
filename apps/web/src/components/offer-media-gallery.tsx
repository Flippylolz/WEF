"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import type { OfferDetail } from "@/lib/catalog-api";
import { mediaAltText, pickMediaDisplayUrl } from "@/lib/offer-presentation";

type OfferMediaGalleryProps = {
  detail: Pick<OfferDetail, "display_name" | "location">;
  media: OfferDetail["media"];
};

export function OfferMediaGallery({ detail, media }: OfferMediaGalleryProps) {
  const t = useTranslations("map");
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const closeLightbox = useCallback(() => setActiveIndex(null), []);
  const showPrevious = useCallback(() => {
    setActiveIndex((current) =>
      current === null ? null : Math.max(0, current - 1),
    );
  }, []);
  const showNext = useCallback(() => {
    setActiveIndex((current) =>
      current === null ? null : Math.min(media.length - 1, current + 1),
    );
  }, [media.length]);

  useEffect(() => {
    if (activeIndex === null) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") closeLightbox();
      if (event.key === "ArrowLeft") showPrevious();
      if (event.key === "ArrowRight") showNext();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, closeLightbox, showNext, showPrevious]);

  if (media.length === 0) {
    return <p className="offer-detail-empty">{t("detailNoMedia")}</p>;
  }

  return (
    <>
      <ul className="offer-media-grid" aria-label={t("detailMediaLabel")}>
        {media.map((item, index) => {
          const displayUrl = pickMediaDisplayUrl(
            item.thumbnail_url,
            item.content_url,
          );
          const alt = mediaAltText(detail, index, media.length);
          return (
            <li key={item.media_asset_id}>
              {displayUrl ? (
                <button
                  className="offer-media-thumb"
                  type="button"
                  aria-label={t("detailOpenMedia", { index: index + 1 })}
                  onClick={() => setActiveIndex(index)}
                >
                  {item.media_type === "image" ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={displayUrl} alt={alt} loading="lazy" />
                  ) : (
                    <span className="offer-media-video-badge">
                      {t("detailVideoBadge")}
                    </span>
                  )}
                </button>
              ) : (
                <div
                  className="offer-media-missing"
                  role="img"
                  aria-label={alt}
                >
                  {t("detailMissingMedia")}
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {activeIndex !== null ? (
        <div
          className="offer-media-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={t("detailMediaLightbox")}
        >
          <div className="offer-media-lightbox-toolbar">
            <button
              type="button"
              onClick={showPrevious}
              disabled={activeIndex === 0}
            >
              {t("detailMediaPrevious")}
            </button>
            <span>
              {t("detailMediaPosition", {
                current: activeIndex + 1,
                total: media.length,
              })}
            </span>
            <button
              type="button"
              onClick={showNext}
              disabled={activeIndex >= media.length - 1}
            >
              {t("detailMediaNext")}
            </button>
            <button type="button" onClick={closeLightbox}>
              {t("detailClose")}
            </button>
          </div>
          <OfferMediaSlide
            item={media[activeIndex]!}
            alt={mediaAltText(detail, activeIndex, media.length)}
          />
        </div>
      ) : null}
    </>
  );
}

type OfferMediaSlideProps = {
  item: OfferDetail["media"][number];
  alt: string;
};

function OfferMediaSlide({ item, alt }: OfferMediaSlideProps) {
  const t = useTranslations("map");
  const displayUrl = pickMediaDisplayUrl(item.thumbnail_url, item.content_url);

  if (!displayUrl) {
    return <p className="offer-detail-empty">{t("detailMissingMedia")}</p>;
  }

  if (item.media_type === "video") {
    return (
      <video
        className="offer-media-video"
        controls
        preload="metadata"
        aria-label={alt}
      >
        <source src={displayUrl} type={item.mime_type} />
      </video>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img className="offer-media-full" src={displayUrl} alt={alt} />
  );
}
