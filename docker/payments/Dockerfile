FROM 21dotco/two1:base
MAINTAINER 21.co

ADD . /usr/src/app

RUN apk add --no-cache linux-headers
RUN pip3 install -r /usr/src/app/requirements.txt
CMD sh -c "python3 /usr/src/app/utils/login.py && sleep 2 && python3 /usr/src/app/server.py"