FROM debian:bookworm-slim

RUN apt update
RUN apt install -y python3 python3-flask gunicorn
RUN mkdir /root/chatalyzer
WORKDIR /root/chatalyzer/engine
CMD ["gunicorn", "server_flask:server", "--bind", "0.0.0.0:5030"]
