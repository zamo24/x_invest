const askButton = document.getElementById("ask");
const messageInput = document.getElementById("message");
const answerEl = document.getElementById("answer");
const statusEl = document.getElementById("status");
const sourcesEl = document.getElementById("sources");
const chatThreadSelect = document.getElementById("chat-thread");
const newThreadButton = document.getElementById("new-thread");
const historyEl = document.getElementById("history");

let selectedChatThreadId = "";
let chatThreads = [];

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error" : "";
}

function renderSources(sources) {
  sourcesEl.innerHTML = "";
  for (const source of sources || []) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = source.tweet_url;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.textContent = source.tweet_url;

    const p = document.createElement("p");
    p.textContent = source.snippet || "";

    li.appendChild(a);
    li.appendChild(p);
    sourcesEl.appendChild(li);
  }
}

function renderHistory(messages) {
  historyEl.innerHTML = "";
  if (!messages || messages.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No messages yet. Ask your first question to start a thread.";
    historyEl.appendChild(empty);
    return;
  }

  for (const message of messages) {
    const item = document.createElement("div");
    item.className = "history-item";

    const role = document.createElement("div");
    role.className = "history-role";
    role.textContent = message.role || "assistant";

    const text = document.createElement("p");
    text.textContent = message.message_text || "";

    item.appendChild(role);
    item.appendChild(text);
    historyEl.appendChild(item);
  }
}

function renderThreadSelect() {
  chatThreadSelect.innerHTML = "";

  const newOption = document.createElement("option");
  newOption.value = "";
  newOption.textContent = "Start a new chat thread";
  chatThreadSelect.appendChild(newOption);

  for (const thread of chatThreads) {
    const option = document.createElement("option");
    option.value = thread.id;
    option.textContent = thread.title || "Untitled chat";
    option.title = thread.title || "";
    chatThreadSelect.appendChild(option);
  }

  chatThreadSelect.value = selectedChatThreadId;
}

function sortThreads(threads) {
  return [...threads].sort((a, b) => {
    const aDate = Date.parse(a.updated_at || a.created_at || 0);
    const bDate = Date.parse(b.updated_at || b.created_at || 0);
    return bDate - aDate;
  });
}

async function loadChatThreads() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "CHAT_THREADS" }, (response) => {
      if (!response?.ok) {
        setStatus(response?.error || "Could not load threads", true);
        resolve();
        return;
      }

      chatThreads = sortThreads(Array.isArray(response.data) ? response.data : []);
      const stillExists =
        selectedChatThreadId &&
        chatThreads.some((thread) => thread.id === selectedChatThreadId);
      if (!stillExists) {
        selectedChatThreadId = "";
      }

      renderThreadSelect();
      resolve();
    });
  });
}

async function loadThreadDetail(threadId) {
  if (!threadId) {
    renderHistory([]);
    return;
  }

  return new Promise((resolve) => {
    chrome.runtime.sendMessage(
      {
        type: "CHAT_THREAD_DETAIL",
        payload: { thread_id: threadId },
      },
      (response) => {
        if (!response?.ok) {
          setStatus(response?.error || "Could not load chat history", true);
          renderHistory([]);
          resolve();
          return;
        }

        const messages = Array.isArray(response?.data?.messages) ? response.data.messages : [];
        renderHistory(messages);
        resolve();
      },
    );
  });
}

async function refreshThreadsAndHistory() {
  await loadChatThreads();
  await loadThreadDetail(selectedChatThreadId);
}

chatThreadSelect.addEventListener("change", async (event) => {
  selectedChatThreadId = event.target.value || "";
  answerEl.textContent = "";
  sourcesEl.innerHTML = "";
  await loadThreadDetail(selectedChatThreadId);
});

newThreadButton.addEventListener("click", async () => {
  selectedChatThreadId = "";
  renderThreadSelect();
  answerEl.textContent = "";
  sourcesEl.innerHTML = "";
  renderHistory([]);
  setStatus("Starting a new chat thread.");
});

askButton.addEventListener("click", async () => {
  const message = messageInput.value.trim();
  if (!message) {
    setStatus("Enter a message first.", true);
    return;
  }

  setStatus("Running...");
  answerEl.textContent = "";
  sourcesEl.innerHTML = "";

  chrome.runtime.sendMessage(
    {
      type: "CHAT",
      payload: {
        message,
        scope: "all",
        chat_thread_id: selectedChatThreadId || undefined,
        top_k: 8,
      },
    },
    async (response) => {
      if (!response?.ok) {
        setStatus(response?.error || "Chat failed", true);
        return;
      }

      answerEl.textContent = response.data?.answer_text || "";
      renderSources(response.data?.cited_sources || []);
      if (response.data?.chat_thread_id) {
        selectedChatThreadId = response.data.chat_thread_id;
      }
      await refreshThreadsAndHistory();
      setStatus("Done");
    },
  );
});

void refreshThreadsAndHistory();
