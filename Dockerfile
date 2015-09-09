FROM 21dotco/base

RUN apt-get update && apt-get -qq install python-scipy libblas-dev liblapack-dev gfortran


RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

RUN pip install -e . --no-cache-dir

RUN python setup.py build_ext --inplace

EXPOSE 8000

ENV PORT 8000
ENV PYTHONUNBUFFERED true

RUN rm Procfile

CMD [ "gunicorn", "--pythonpath", "two1/djangobitcoin", "djangobitcoin.wsgi", "--worker-class", "tornado"]
