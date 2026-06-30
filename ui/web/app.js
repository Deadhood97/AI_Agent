const state = {
  sessionId: "",
  suggestions: [],
  previewRows: [],
  datasetLoaded: false,
};

const els = {
  composerForm: document.querySelector("#composerForm"),
  csvFile: document.querySelector("#csvFile"),
  fileLabel: document.querySelector("#fileLabel"),
  description: document.querySelector("#description"),
  questionInput: document.querySelector("#questionInput"),
  sendButton: document.querySelector("#sendButton"),
  chatThread: document.querySelector("#chatThread"),
  emptyState: document.querySelector("#emptyState"),
  suggestions: document.querySelector("#suggestions"),
  datasetStatus: document.querySelector("#datasetStatus"),
  inspectorState: document.querySelector("#inspectorState"),
  runStatus: document.querySelector("#runStatus"),
  rowCount: document.querySelector("#rowCount"),
  columnCount: document.querySelector("#columnCount"),
  sessionId: document.querySelector("#sessionId"),
  tableWrap: document.querySelector(".table-wrap"),
  previewTable: document.querySelector("#previewTable"),
  previewMeta: document.querySelector("#previewMeta"),
  planBody: document.querySelector("#planBody"),
  traceBody: document.querySelector("#traceBody"),
  tabButtons: document.querySelectorAll(".tab-button"),
  tabPanels: document.querySelectorAll(".tab-panel"),
};

document.querySelectorAll("button").forEach((button) => {
  button.dataset.initiallyDisabled = String(button.disabled);
});

function setStatus(text, mode = "") {
  els.runStatus.textContent = text;
  els.runStatus.className = `status-dot ${mode}`.trim();
}

function setDatasetStatus(text, mode = "") {
  els.datasetStatus.textContent = text;
  els.datasetStatus.className = `status-chip ${mode}`.trim();
}

function setBusy(isBusy) {
  document.querySelectorAll("button").forEach((button) => {
    if (button.dataset.initiallyDisabled === "true") {
      button.disabled = true;
      return;
    }
    button.disabled = isBusy && !button.classList.contains("tab-button");
  });
  els.questionInput.disabled = isBusy;
  els.description.disabled = isBusy;
  els.csvFile.disabled = isBusy;
}

function showTab(tabName) {
  els.tabButtons.forEach((button) => {
    const isActive = button.dataset.tab === tabName;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  els.tabPanels.forEach((panel) => {
    const isActive = panel.id === `tab-${tabName}`;
    panel.classList.toggle("active", isActive);
    panel.hidden = !isActive;
  });
}

function removeEmptyState() {
  if (els.emptyState) {
    els.emptyState.remove();
    els.emptyState = null;
  }
}

function addMessage(role, text, meta = "") {
  removeEmptyState();
  const message = document.createElement("article");
  message.className = `message ${role}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Analyst";
  if (meta) {
    const metaSpan = document.createElement("span");
    metaSpan.textContent = meta;
    label.appendChild(metaSpan);
  }

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;

  message.appendChild(label);
  message.appendChild(bubble);
  els.chatThread.appendChild(message);
  els.chatThread.scrollTop = els.chatThread.scrollHeight;
  return bubble;
}

function clearThreadWithMessage(text) {
  els.chatThread.innerHTML = "";
  els.emptyState = null;
  addMessage("assistant", text);
}

function renderSuggestions(suggestions) {
  els.suggestions.innerHTML = "";
  if (!suggestions.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Upload data to generate starter prompts.";
    els.suggestions.appendChild(empty);
    return;
  }

  suggestions.slice(0, 3).forEach((suggestion) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "suggestion";
    button.textContent = suggestion.question;
    button.addEventListener("click", () => {
      els.questionInput.value = suggestion.question;
      els.questionInput.focus();
    });
    els.suggestions.appendChild(button);
  });
}

function renderPreview(rows) {
  els.previewTable.innerHTML = "";
  els.tableWrap.classList.toggle("has-preview", Boolean(rows && rows.length));
  if (!rows || !rows.length) {
    els.previewTable.innerHTML = '<tbody><tr><td class="preview-empty">Preview appears after upload.</td></tr></tbody>';
    return;
  }

  const columns = Object.keys(rows[0]);
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => {
      const td = document.createElement("td");
      const value = row[column];
      td.textContent = value === null || value === undefined ? "" : String(value);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  els.previewTable.appendChild(thead);
  els.previewTable.appendChild(tbody);
}

async function parseJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || "Request failed.");
    error.payload = payload;
    throw error;
  }
  return payload;
}

async function uploadDataset(file) {
  const formData = new FormData();
  formData.append("csv_file", file);
  formData.append("description", els.description.value);
  return parseJsonResponse(await fetch("/api/upload", { method: "POST", body: formData }));
}

async function askQuestion(question) {
  return parseJsonResponse(
    await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId, question }),
    }),
  );
}

function applyUploadPayload(payload, fileName) {
  state.sessionId = payload.session_id;
  state.suggestions = payload.suggested_questions || [];
  state.previewRows = payload.preview || [];
  state.datasetLoaded = true;

  els.inspectorState.textContent = payload.filename || fileName;
  els.rowCount.textContent = Number(payload.row_count).toLocaleString();
  els.columnCount.textContent = Number(payload.column_count).toLocaleString();
  els.sessionId.textContent = payload.session_id;
  els.previewMeta.textContent = `${state.previewRows.length} preview rows`;
  setDatasetStatus("Dataset loaded", "good");

  renderSuggestions(state.suggestions);
  renderPreview(state.previewRows);
  showTab("data");

  clearThreadWithMessage(
    `Dataset loaded: ${payload.filename || fileName}\n${Number(payload.row_count).toLocaleString()} rows, ${Number(
      payload.column_count,
    ).toLocaleString()} columns.\nPick a starter prompt or ask your own follow-up.`,
  );
}

function applyAnswerPayload(payload, pendingBubble) {
  pendingBubble.textContent = payload.answer || "No answer returned.";
  els.planBody.textContent = JSON.stringify(payload.analysis_plan || {}, null, 2);
  els.traceBody.textContent = JSON.stringify(
    {
      trace: payload.trace || [],
      output_key: payload.output_key,
      turn_id: payload.turn_id,
      status: payload.status,
    },
    null,
    2,
  );
  showTab("plan");
}

function applyErrorPayload(error, pendingBubble = null) {
  const payload = error.payload || {};
  const message = error.message || "Request failed.";
  if (pendingBubble) {
    pendingBubble.textContent = message;
  } else {
    addMessage("assistant", message);
  }

  if (payload.attempts) {
    els.planBody.textContent = JSON.stringify({ attempts: payload.attempts }, null, 2);
    els.traceBody.textContent = JSON.stringify(
      {
        error: payload.error,
        error_type: payload.error_type,
        attempts: payload.attempts,
      },
      null,
      2,
    );
    showTab("plan");
  }
}

els.tabButtons.forEach((button) => {
  button.addEventListener("click", () => showTab(button.dataset.tab));
});

els.csvFile.addEventListener("change", () => {
  const file = els.csvFile.files[0];
  els.fileLabel.textContent = file ? file.name : "Attach CSV";
});

els.composerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = els.csvFile.files[0];
  const question = els.questionInput.value.trim();

  if (!file && !state.datasetLoaded) {
    addMessage("assistant", "Attach a CSV first, then I can analyze it.");
    setStatus("Needs data", "warn");
    return;
  }
  if (!question && state.datasetLoaded && !file) {
    addMessage("assistant", "Ask a question or choose one of the starter prompts.");
    setStatus("Needs prompt", "warn");
    return;
  }

  setBusy(true);
  setStatus("Working", "warn");
  let pendingBubble = null;

  try {
    if (file) {
      setDatasetStatus("Uploading", "warn");
      clearThreadWithMessage("Reading the dataset and preparing starter prompts...");
      const uploadPayload = await uploadDataset(file);
      applyUploadPayload(uploadPayload, file.name);
      els.csvFile.value = "";
      els.fileLabel.textContent = "Attach CSV";
    }

    if (question) {
      addMessage("user", question);
      els.questionInput.value = "";
      pendingBubble = addMessage("assistant", "Planning and executing the analysis...", "running");
      const answerPayload = await askQuestion(question);
      applyAnswerPayload(answerPayload, pendingBubble);
      setStatus(answerPayload.status || "Answered", "good");
    } else {
      setStatus("Ready", "good");
    }
  } catch (error) {
    applyErrorPayload(error, pendingBubble);
    setStatus("Error", "warn");
    if (!state.datasetLoaded) {
      setDatasetStatus("No dataset", "warn");
    }
  } finally {
    setBusy(false);
  }
});

renderSuggestions([]);
renderPreview([]);
showTab("data");
