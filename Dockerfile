FROM python:3.9.5
WORKDIR /usr/src/app
COPY . /usr/src/app
RUN ls -la .
RUN pip install -r requirements.txt
CMD ["main.py"]
ENTRYPOINT ["python3"] 
