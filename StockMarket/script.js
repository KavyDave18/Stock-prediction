let stockChart = null; // to hold chart instance

document.getElementById("predict-btn").addEventListener("click", async () => {
  const ticker = document.getElementById("ticker-input").value.trim();
  const errorMessage = document.getElementById("error-message");
  const resultsSection = document.getElementById("results-section");
  const infoSection = document.getElementById("info-section");

  if (!ticker) {
    errorMessage.innerText = "Please enter a stock ticker!";
    errorMessage.style.display = "block";
    return;
  }
  errorMessage.style.display = "none";

  // Show loading spinner
  const btnText = document.querySelector(".btn-text");
  const btnLoading = document.querySelector(".btn-loading");
  btnText.style.display = "none";
  btnLoading.style.display = "inline-flex";

  try {
    const response = await fetch("http://127.0.0.1:5000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: ticker, days: 1, window: 5 }),
    });

    const data = await response.json();

    if (data.error) {
      errorMessage.innerText = data.error;
      errorMessage.style.display = "block";
      return;
    }

    // Fill in prediction card
    document.getElementById("ticker-display").innerText = data.ticker;
    document.getElementById("current-price").innerText = `$${data.last_close}`;
    document.getElementById("predicted-price").innerText = `$${data.predicted_price}`;

    const change = (data.predicted_price - data.last_close).toFixed(2);
    const percent = ((change / data.last_close) * 100).toFixed(2);

    document.getElementById("price-change").innerText = `$${change}`;
    document.getElementById("percent-change").innerText = `${percent}%`;

    // Badge
    const badge = document.getElementById("change-badge");
    badge.innerText = change >= 0 ? "Bullish ↑" : "Bearish ↓";
    badge.className = "badge " + (change >= 0 ? "positive" : "negative");

    // Show sections
    resultsSection.style.display = "block";
    infoSection.style.display = "none";

    // Chart data
    const labels = [...data.history.dates, ...data.predicted.map(p => p.date)];
    const prices = [...data.history.closes, ...data.predicted.map(p => p.price)];

    // Destroy old chart if exists
    if (stockChart) stockChart.destroy();

    const ctx = document.getElementById("stock-chart").getContext("2d");
    stockChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Historical",
            data: data.history.closes,
            borderColor: "blue",
            tension: 0.2,
          },
          {
            label: "Predicted",
            data: [...new Array(data.history.closes.length - 1).fill(null), data.last_close, ...data.predicted.map(p => p.price)],
            borderColor: "red",
            borderDash: [5, 5],
            tension: 0.2,
          }
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: true },
        },
        scales: {
          x: { title: { display: true, text: "Date" } },
          y: { title: { display: true, text: "Price (USD)" } },
        },
      },
    });

  } catch (err) {
    errorMessage.innerText = "Error connecting to server.";
    errorMessage.style.display = "block";
  } finally {
    // Reset button state
    btnText.style.display = "inline";
    btnLoading.style.display = "none";
  }
});
