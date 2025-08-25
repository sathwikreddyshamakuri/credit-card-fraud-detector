FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY artifacts ./artifacts

CMD [ "app.lambda_handler.handler" ]