# Test-only tooling. No repository source enters this build context or image.
FROM python:3.14.8-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83 AS python
# This immutable digest reports v44-pre-test3-2-gf65e; no floating binary is used.
FROM kcov/kcov:latest@sha256:481289ae32e55e5b733019515acd10948a4f76dfed381765577db909664fc603
COPY --from=python /usr/local/bin/python3.14 /usr/local/bin/python3.14
COPY --from=python /usr/local/lib/libpython3.14.so.1.0 /usr/local/lib/
COPY --from=python /usr/local/lib/python3.14 /usr/local/lib/python3.14
RUN ln -sfn python3.14 /usr/local/bin/python3 \
    && ln -sfn python3.14 /usr/local/bin/python \
    && ldconfig \
    && python3 -c 'import sys, ssl, hashlib, sqlite3, ctypes; assert sys.version_info[:3] == (3, 14, 8); print(sys.version)' \
    && kcov --version
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["/usr/local/bin/kcov"]
