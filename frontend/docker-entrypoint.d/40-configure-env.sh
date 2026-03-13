#!/bin/sh
set -eu

: "${FRONTEND_PUBLIC_API1_URL:=/api1}"
: "${FRONTEND_PUBLIC_API2_URL:=/api2}"

envsubst '${FRONTEND_PUBLIC_API1_URL} ${FRONTEND_PUBLIC_API2_URL}' \
  < /usr/share/nginx/html/config.template.js \
  > /usr/share/nginx/html/config.js
