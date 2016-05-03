FROM two1:base

ADD . /usr/src/app

RUN apk add --no-cache linux-headers
RUN pip3 install -r /usr/src/app/requirements.txt
RUN apk add --no-cache expect
