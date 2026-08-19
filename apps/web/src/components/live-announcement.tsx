"use client";

type LiveAnnouncementProps = {
  message: string | null;
};

export function LiveAnnouncement({ message }: LiveAnnouncementProps) {
  return (
    <div aria-live="polite" aria-atomic="true" className="sr-only">
      {message ?? ""}
    </div>
  );
}
