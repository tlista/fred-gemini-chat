/**
 * FRED + Gemini Chat Client Application
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatStream = document.getElementById("chatStream");
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const clearChatBtn = document.getElementById("clearChatBtn");

  // Status Badges
  const geminiStatusBadge = document.getElementById("geminiStatusBadge");
  const fredStatusBadge = document.getElementById("fredStatusBadge");
  const modelBadge = document.getElementById("modelBadge");

  // Settings Modal
  const settingsModal = document.getElementById("settingsModal");
  const openSettingsBtn = document.getElementById("openSettingsBtn");
  const closeSettingsBtn = document.getElementById("closeSettingsBtn");
  const saveSettingsBtn = document.getElementById("saveSettingsBtn");
  const testKeysBtn = document.getElementById("testKeysBtn");
  const testResultMsg = document.getElementById("testResultMsg");
  const geminiKeyInput = document.getElementById("geminiKeyInput");
  const fredKeyInput = document.getElementById("fredKeyInput");
  const modelSelect = document.getElementById("modelSelect");

  // Active chart instances to prevent memory leaks / overlap
  const activeCharts = {};

  // Chat message history
  let conversationHistory = [];

  // 1. Initialize configuration from LocalStorage
  function loadSettings() {
    const savedGeminiKey = localStorage.getItem("gemini_api_key") || "";
    const savedFredKey = localStorage.getItem("fred_api_key") || "";
    const savedModel = localStorage.getItem("selected_model") || "gemini-2.5-flash";

    geminiKeyInput.value = savedGeminiKey;
    fredKeyInput.value = savedFredKey;
    modelSelect.value = savedModel;
    modelBadge.textContent = savedModel;

    updateStatusBadges();
  }

  function saveSettings() {
    localStorage.setItem("gemini_api_key", geminiKeyInput.value.trim());
    localStorage.setItem("fred_api_key", fredKeyInput.value.trim());
    localStorage.setItem("selected_model", modelSelect.value);

    modelBadge.textContent = modelSelect.value;
    updateStatusBadges();
    settingsModal.classList.remove("open");
  }

  async function updateStatusBadges() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();

      const userGeminiKey = localStorage.getItem("gemini_api_key") || "";
      const userFredKey = localStorage.getItem("fred_api_key") || "";

      if (userGeminiKey || data.has_gemini_env_key) {
        geminiStatusBadge.textContent = "Gemini: Connected";
        geminiStatusBadge.className = "status-badge badge-success";
      } else {
        geminiStatusBadge.textContent = "Gemini: Demo Mode";
        geminiStatusBadge.className = "status-badge badge-warning";
      }

      if (userFredKey || data.has_fred_env_key) {
        fredStatusBadge.textContent = "FRED: Live API";
        fredStatusBadge.className = "status-badge badge-success";
      } else {
        fredStatusBadge.textContent = "FRED: Offline/Demo Data";
        fredStatusBadge.className = "status-badge badge-warning";
      }
    } catch (e) {
      console.warn("Health check error:", e);
    }
  }

  // 2. Test Keys API
  async function testKeys() {
    testResultMsg.className = "test-result-box";
    testResultMsg.textContent = "Testing API keys connection...";
    testResultMsg.classList.remove("hidden");

    try {
      const res = await fetch("/api/test-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gemini_api_key: geminiKeyInput.value.trim(),
          fred_api_key: fredKeyInput.value.trim(),
        }),
      });

      const data = await res.json();
      let msg = "";
      let allGood = true;

      if (data.gemini_valid) {
        msg += `✅ Gemini: ${data.gemini_message}\n`;
      } else {
        msg += `⚠️ Gemini: ${data.gemini_message}\n`;
        allGood = false;
      }

      if (data.fred_valid) {
        msg += `✅ FRED: ${data.fred_message}`;
      } else {
        msg += `⚠️ FRED: ${data.fred_message}`;
        allGood = false;
      }

      testResultMsg.textContent = msg;
      testResultMsg.className = `test-result-box ${allGood ? "test-success" : "test-fail"}`;
    } catch (e) {
      testResultMsg.textContent = `Connection test error: ${e.message}`;
      testResultMsg.className = "test-result-box test-fail";
    }
  }

  // 3. Chat UI rendering
  function appendMessage(role, content, toolCalls = [], charts = []) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "👤" : "🏛️";

    const body = document.createElement("div");
    body.className = "message-body";

    // If assistant message and tools were called, render tool accordion
    if (toolCalls && toolCalls.length > 0) {
      const toolsContainer = document.createElement("div");
      toolsContainer.className = "tool-calls-container";

      toolCalls.forEach((tool) => {
        const card = document.createElement("div");
        card.className = "tool-call-card";

        const header = document.createElement("div");
        header.className = "tool-call-header";
        header.innerHTML = `
          <div class="tool-call-title">
            <span>🛠️</span>
            <strong>${tool.tool_name}</strong>
          </div>
          <span class="tool-duration">${tool.execution_time_ms}ms ▼</span>
        `;

        const details = document.createElement("div");
        details.className = "tool-call-body";
        details.style.display = "none";
        details.textContent = `Arguments:\n${JSON.stringify(tool.arguments, null, 2)}\n\nResult:\n${tool.result_summary}`;

        header.addEventListener("click", () => {
          const isHidden = details.style.display === "none";
          details.style.display = isHidden ? "block" : "none";
          header.querySelector(".tool-duration").textContent = `${tool.execution_time_ms}ms ${isHidden ? "▲" : "▼"}`;
        });

        card.appendChild(header);
        card.appendChild(details);
        toolsContainer.appendChild(card);
      });

      body.appendChild(toolsContainer);
    }

    // Markdown text rendering
    const textContentDiv = document.createElement("div");
    if (typeof marked !== "undefined" && marked.parse) {
      textContentDiv.innerHTML = marked.parse(content);
    } else {
      textContentDiv.textContent = content;
    }
    body.appendChild(textContentDiv);

    // If charts generated, render interactive Chart.js widgets
    if (charts && charts.length > 0) {
      charts.forEach((chartData) => {
        const chartCard = createChartCard(chartData);
        body.appendChild(chartCard);
      });
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(body);
    chatStream.appendChild(msgDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function appendLoadingMessage() {
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "message assistant-message loading-indicator-msg";
    loadingDiv.id = "loadingMessage";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "🏛️";

    const body = document.createElement("div");
    body.className = "message-body";
    body.innerHTML = `
      <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 6px;">
        Gemini is consulting the FRED API database...
      </div>
      <div class="loading-dots"><span></span><span></span><span></span></div>
    `;

    loadingDiv.appendChild(avatar);
    loadingDiv.appendChild(body);
    chatStream.appendChild(loadingDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function removeLoadingMessage() {
    const loading = document.getElementById("loadingMessage");
    if (loading) loading.remove();
  }

  // 4. Interactive Chart Builder using Chart.js
  function createChartCard(chartData) {
    const card = document.createElement("div");
    card.className = "chart-container-card";

    const header = document.createElement("div");
    header.className = "chart-header";
    header.innerHTML = `
      <span class="chart-title">📊 ${chartData.title}</span>
    `;

    const canvasWrapper = document.createElement("div");
    canvasWrapper.className = "chart-canvas-wrapper";

    const canvas = document.createElement("canvas");
    canvas.id = chartData.chart_id;
    canvasWrapper.appendChild(canvas);

    card.appendChild(header);
    card.appendChild(canvasWrapper);

    // Render chart once attached to DOM
    setTimeout(() => {
      renderChart(canvas, chartData);
    }, 50);

    return card;
  }

  function renderChart(canvas, chartData) {
    if (typeof Chart === "undefined") {
      console.warn("Chart.js library is not loaded");
      return;
    }

    // Palette of high-contrast financial colors
    const colors = [
      { border: "#58a6ff", bg: "rgba(88, 166, 255, 0.15)" },
      { border: "#d29922", bg: "rgba(210, 153, 34, 0.15)" },
      { border: "#3fb950", bg: "rgba(63, 185, 80, 0.15)" },
      { border: "#bc8cff", bg: "rgba(188, 140, 255, 0.15)" },
      { border: "#f85149", bg: "rgba(248, 81, 73, 0.15)" },
    ];

    // Collect all unique labels (dates) in chronological order
    const allDatesSet = new Set();
    chartData.series_list.forEach((s) => {
      (s.dates || []).forEach((d) => allDatesSet.add(d));
    });
    const labels = Array.from(allDatesSet).sort();

    const datasets = chartData.series_list.map((series, idx) => {
      const color = colors[idx % colors.length];
      const dateValueMap = new Map();
      (series.dates || []).forEach((d, i) => {
        dateValueMap.set(d, series.values[i]);
      });

      const alignedData = labels.map((d) => dateValueMap.get(d) ?? null);

      return {
        label: `${series.name} (${series.units || "Value"})`,
        data: alignedData,
        borderColor: color.border,
        backgroundColor: color.bg,
        borderWidth: 2,
        tension: 0.2,
        fill: chartData.series_list.length === 1,
        pointRadius: labels.length > 40 ? 1 : 3,
        pointHoverRadius: 6,
      };
    });

    const ctx = canvas.getContext("2d");
    activeCharts[chartData.chart_id] = new Chart(ctx, {
      type: chartData.chart_type === "bar" ? "bar" : "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            position: "top",
            labels: {
              color: "#c9d1d9",
              font: { size: 12 },
            },
          },
          tooltip: {
            backgroundColor: "#161b22",
            borderColor: "#30363d",
            borderWidth: 1,
            titleColor: "#f0f6fc",
            bodyColor: "#c9d1d9",
            padding: 10,
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: {
              color: "#8b949e",
              maxTicksLimit: 12,
            },
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#8b949e" },
            title: {
              display: !!chartData.y_axis_label,
              text: chartData.y_axis_label,
              color: "#8b949e",
            },
          },
        },
      },
    });
  }

  // 5. Send User Message
  async function handleSendMessage(userText) {
    if (!userText || !userText.trim()) return;

    const message = userText.trim();
    chatInput.value = "";
    chatInput.style.height = "auto";
    sendBtn.disabled = true;

    // Render user bubble
    appendMessage("user", message);
    appendLoadingMessage();

    try {
      const payload = {
        message: message,
        history: conversationHistory,
        model: localStorage.getItem("selected_model") || "gemini-2.5-flash",
        gemini_api_key: localStorage.getItem("gemini_api_key") || undefined,
        fred_api_key: localStorage.getItem("fred_api_key") || undefined,
      };

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      removeLoadingMessage();

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        appendMessage("assistant", `⚠️ **Error**: ${errData.detail || "Failed to process prompt."}`);
        return;
      }

      const data = await res.json();
      conversationHistory = data.history || [];

      appendMessage("assistant", data.reply, data.tool_calls, data.charts);
    } catch (err) {
      removeLoadingMessage();
      appendMessage("assistant", `⚠️ **Network / Server Error**: ${err.message}`);
    } finally {
      sendBtn.disabled = false;
      chatInput.focus();
    }
  }

  // 6. Event Listeners
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendMessage(chatInput.value);
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(chatInput.value);
    }
  });

  // Auto-resize textarea
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = `${Math.min(chatInput.scrollHeight, 140)}px`;
  });

  // Clear chat
  clearChatBtn.addEventListener("click", () => {
    conversationHistory = [];
    chatStream.innerHTML = "";
    appendMessage(
      "assistant",
      "Conversation cleared. How can I assist your economic analysis today?"
    );
  });

  // Quick suggestion chips & pills
  document.addEventListener("click", (e) => {
    const pill = e.target.closest(".suggestion-pill, .chip");
    if (pill) {
      const query = pill.getAttribute("data-query");
      if (query) {
        handleSendMessage(query);
      }
    }
  });

  // Modal open/close
  openSettingsBtn.addEventListener("click", () => {
    testResultMsg.classList.add("hidden");
    settingsModal.classList.add("open");
  });

  closeSettingsBtn.addEventListener("click", () => {
    settingsModal.classList.remove("open");
  });

  saveSettingsBtn.addEventListener("click", saveSettings);
  testKeysBtn.addEventListener("click", testKeys);

  // Close modal when clicking outside
  settingsModal.addEventListener("click", (e) => {
    if (e.target === settingsModal) {
      settingsModal.classList.remove("open");
    }
  });

  // Init
  loadSettings();
});
