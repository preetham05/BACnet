FROM python:2.7-slim

WORKDIR /app
ADD . /app
RUN pip install bacpypes
EXPOSE 47808
EXPOSE 47809
EXPOSE 80
#CMD ["python", "server.py"]
CMD ["bash", "run.sh"]
#CMD ["bash"]

