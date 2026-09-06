"use client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type { Account } from "@/lib/auth-api";
import { revealOfferContacts, type RevealedContact } from "@/lib/contacts-api";

type ContactRevealSectionProps = {
  offerId: string;
  account: Account | null | undefined;
  onRequestSignIn: () => void;
  onRequestPasswordChange: () => void;
};

export function ContactRevealSection({
  offerId,
  account,
  onRequestSignIn,
  onRequestPasswordChange,
}: ContactRevealSectionProps) {
  const t = useTranslations("map");
  const [contacts, setContacts] = useState<RevealedContact[] | null>(null);
  const [errorCode, setErrorCode] = useState<
    | "unauthorized"
    | "forbidden"
    | "not_found"
    | "rate_limited"
    | "unavailable"
    | "unknown"
    | null
  >(null);
  const [loading, setLoading] = useState(false);

  const signedIn = account != null;
  const mustChange = Boolean(account?.must_change_password);

  return (
    <section
      className="offer-detail-contacts"
      aria-label={t("detailContactsLabel")}
    >
      <h3>{t("detailContactsLabel")}</h3>
      {!signedIn ? (
        <>
          <p>{t("detailRevealSignInRequired")}</p>
          <button
            className="button-primary"
            type="button"
            onClick={onRequestSignIn}
          >
            {t("detailRevealSignInAction")}
          </button>
        </>
      ) : mustChange ? (
        <>
          <p>{t("detailRevealPasswordRequired")}</p>
          <button
            className="button-primary"
            type="button"
            onClick={onRequestPasswordChange}
          >
            {t("detailRevealPasswordAction")}
          </button>
        </>
      ) : contacts !== null ? (
        contacts.length === 0 ? (
          <p role="status">{t("detailRevealEmpty")}</p>
        ) : (
          <ul className="offer-detail-contact-list">
            {contacts.map((contact) => (
              <li key={`${contact.kind}:${contact.masked_value}`}>
                <span>{t(`detailRevealKind.${contact.kind}`)}</span>
                <strong>{contact.value}</strong>
              </li>
            ))}
          </ul>
        )
      ) : (
        <>
          <button
            className="button-primary"
            type="button"
            disabled={loading}
            onClick={async () => {
              setLoading(true);
              setErrorCode(null);
              const result = await revealOfferContacts(offerId);
              setLoading(false);
              if (result.state === "error") {
                setErrorCode(result.code ?? "unknown");
                return;
              }
              setContacts(result.data.contacts);
            }}
          >
            {loading ? t("detailRevealLoading") : t("detailRevealContacts")}
          </button>
          {errorCode ? (
            <p className="form-error" role="alert">
              {t(`detailRevealError.${errorCode}`)}
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
