FROM 21dotco/two1:base
MAINTAINER 21.co

ADD . /usr/src/app

RUN apk add --no-cache linux-headers
RUN pip3 install -r /usr/src/app/requirements.txt