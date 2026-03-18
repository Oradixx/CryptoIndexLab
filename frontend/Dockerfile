FROM nginxinc/nginx-unprivileged:1.27.5-alpine

USER root

RUN apk upgrade --no-cache \
    && apk add --no-cache gettext

WORKDIR /usr/share/nginx/html

COPY --chown=nginx:nginx src/ ./
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx --chmod=755 docker-entrypoint.d/40-configure-env.sh /docker-entrypoint.d/40-configure-env.sh

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/ || exit 1
