FROM python:3.10-alpine

RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests

COPY main.py /app/main.py

WORKDIR /app

CMD python main.py
