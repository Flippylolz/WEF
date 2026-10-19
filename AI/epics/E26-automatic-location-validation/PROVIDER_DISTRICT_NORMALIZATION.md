# Canary-discovered provider district normalization

The first live observation on 6 September 2026 returned matching street candidates
with confidence 1.00 for Ostrzycka and both Jugosłowiańska cases, but the provider
placed `South Praga` in `suburb`. The adapter did not recognize that translation
as Praga-Południe, so it retained an unrelated neighborhood and lacked the required
district evidence. Application was not enabled. The obsolete observation target
was paused to conserve the unchanged daily provider budget.

This standalone E26 defect correction recognizes exactly `South Praga` and
`North Praga` in provider district/suburb evidence, with case/Unicode folding.
The equivalence with Praga-Południe and Praga-Północ is independently documented
in [Stępniak, Geographia Polonica 85(1), page 71 (2012)](https://rcin.org.pl/Content/28367/WA51_46733_r2012-t85-no1_G-Polonica-Stepniak.pdf).
Source normalization, confidence, city/country, street/number matching, protection,
geometry and quota rules are unchanged. Unknown translations and explicit district
conflicts still fail closed. A district translation cannot supply a building number.

Request version `forward-geocode-v4` (including its street form) invalidates the
cached v3 provider interpretation and creates a fresh durable revalidation target.
Normalizer `warsaw-address-v3` and review policy `warsaw-review-v2` are unchanged.
The prior generation remains paused with its immutable observation receipts.
The new generation starts in observation mode and must repeat the same ten-canary
source/identity/geometry/public verification before any application or expansion.
No selection has been altered by the paused v3 observation.

Tests cover both translations, source Gocław context, unknown and conflicting
districts, exact street precision, and rejection of the old cached interpretation
with subsequent new-cache reuse. `UV_PYTHON=3.13.2 make verify` passed:
1,287 backend tests, 185 frontend tests, 186 script tests and all required
format/lint/types/contracts/coverage/runtime/build/architecture checks.
Current-head CI and release remain required before repeating the live canary.
