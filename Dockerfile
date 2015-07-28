FROM python:3-onbuild

RUN python setup.py build_ext --inplace

CMD [ "python" ]