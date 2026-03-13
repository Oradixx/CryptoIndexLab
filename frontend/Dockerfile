FROM nginx:1.27-alpine

RUN apk add --no-cache gettext

WORKDIR /usr/share/nginx/html

COPY src/ ./
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/40-configure-env.sh /docker-entrypoint.d/40-configure-env.sh

RUN chmod +x /docker-entrypoint.d/40-configure-env.sh

EXPOSE 80
