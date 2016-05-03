FROM alpine:3.3

RUN apk add --no-cache nginx

RUN rm /etc/nginx/nginx.conf
RUN rm /etc/nginx/nginx.conf.default
COPY files/nginx.conf /etc/nginx/nginx.conf
ADD sites-enabled/ /etc/nginx/sites-enabled
ADD sites-available/ /etc/nginx/sites-available
