FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel ^
 && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY artifacts ./artifacts

CMD [ "app.lambda_handler.handler" ]
