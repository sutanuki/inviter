FROM python:3.13
WORKDIR /bot

COPY requirements.txt /bot/
RUN pip install --root-user-action=ignore -r requirements.txt
COPY . /bot

EXPOSE 8080

# 両方を起動：bot.py と FastAPI（バックグラウンド）
CMD uvicorn app.server:app --host 0.0.0.0 --port 8080 & python app/bot.py