# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
# Allow browser calls (localhost:3000, file://, etc.). Lock down origins in production.
CORS(app)

# ---------- Helpers ----------
def fetch_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Download historical data. Returns a DataFrame with a DateTimeIndex and a 'Close' column.
    """
    df = yf.download(
        ticker.strip().upper(),
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )
    if df.empty or "Close" not in df.columns:
        raise ValueError(f"No price data found for ticker '{ticker}'.")
    return df[["Close"]].dropna()

def build_supervised(close_series: pd.Series, window: int):
    vals = close_series.values.astype(float)
    X, y = [], []
    for i in range(window, len(vals)):
        X.append(vals[i - window : i])
        y.append(vals[i])
    X = np.array(X).reshape(len(X), -1)   # <--- important fix
    y = np.array(y)
    return X, y

def train_and_forecast(close_series: pd.Series, days: int, window: int):
    X, y = build_supervised(close_series, window)
    if len(X) < 10:
        raise ValueError("Not enough data to train the model.")

    model = LinearRegression()
    model.fit(X, y)

    last_window = close_series.values[-window:].astype(float)
    preds = []
    for _ in range(days):
        # always reshape into (1, window)
        next_price = float(model.predict(last_window.reshape(1, -1))[0])
        preds.append(next_price)

        last_window = np.roll(last_window, -1)
        last_window[-1] = next_price
    return preds


def to_2dp_list(xs):
    return [round(float(x), 2) for x in xs]

# ---------- Routes ----------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/predict", methods=["POST"])
def predict():
    """
    Request JSON:
      {
        "ticker": "AAPL",
        "days": 1,            # optional, default 1, max 7
        "window": 5,          # optional lag window (2..30)
        "period": "1y"        # optional yfinance period (e.g., "6mo","1y","2y")
      }

    Response JSON:
      {
        "ticker": "AAPL",
        "last_close": 215.34,
        "days": 1,
        "window": 5,
        "history": { "dates": [...], "closes": [...] },  # last 30 business days
        "predicted": [ { "date": "2025-08-21", "price": 217.12 }, ... ],
        "predicted_price": 217.12   # convenience: last predicted value
      }
    """
    try:
        data = request.get_json(force=True) or {}
        ticker = str(data.get("ticker", "")).strip().upper()
        if not ticker:
            return jsonify({"error": "Missing 'ticker'."}), 400

        days = int(data.get("days", 1))
        days = max(1, min(days, 7))  # cap to 7 days

        window = int(data.get("window", 5))
        if window < 2 or window > 30:
            return jsonify({"error": "'window' must be between 2 and 30."}), 400

        period = str(data.get("period", "1y"))

        # 1) Fetch data
        df = fetch_history(ticker, period=period, interval="1d")
        close = df["Close"]

        # 2) Train + forecast next business days
        preds = train_and_forecast(close, days=days, window=window)

        # 3) Build dates for predictions (business days after last date)
        last_date = close.index[-1]
        pred_dates = [(last_date + BDay(i)).date().isoformat() for i in range(1, days + 1)]

        # 4) History for chart (last 30 business days)
        hist_tail = close.tail(30)
        history = {
            "dates": [d.date().isoformat() for d in hist_tail.index],
            "closes": to_2dp_list(hist_tail.values),
        }

        # 5) Response
        predicted = [{"date": d, "price": round(p, 2)} for d, p in zip(pred_dates, preds)]
        resp = {
            "ticker": ticker,
            "last_close": round(float(close.iloc[-1]), 2),
            "days": days,
            "window": window,
            "history": history,
            "predicted": predicted,
            "predicted_price": predicted[-1]["price"],  # convenience for simple UIs
        }
        return jsonify(resp), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        # log e in real apps
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    # Run on 0.0.0.0 if you want to access from phone on same Wi-Fi
    app.run(debug=True, host="127.0.0.1", port=5000)
