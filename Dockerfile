FROM python:2.7.10
MAINTAINER poly <mcx_221@foxmail.com>

RUN apt-get update && apt-get install -y postgresql sudo
RUN sed -ie 's/md5/trust/' /etc/postgresql/9.4/main/pg_hba.conf
RUN service postgresql start

ENV HN_UPDATE_KEY mysecretkey
RUN echo "10 * * * * curl -L 'http://localhost:5000/update' -d key=\$(cat /var/hndigest-update-key)" | crontab -

RUN mkdir /app
WORKDIR /app
# For cache
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app/

EXPOSE 5000
CMD if [ "$HN_UPDATE_KEY" = "mysecretkey" ]; then echo "[Warning] You should set HN_UPDATE_KEY in the environment"; fi && \
    echo -n ${HN_UPDATE_KEY}>/var/hndigest-update-key && \
	service postgresql start && \
    cron && \
    make run-in-docker
