const askButton = document.getElementById("ask");
const messageInput = document.getElementById("message");
const answerEl = document.getElementById("answer");
const statusEl = document.getElementById("status");
const sourcesEl = document.getElementById("sources");

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

askButton.addEventListener("click", async () => {
  setStatus("Running...");
  answerEl.textContent = "";
  sourcesEl.innerHTML = "";

  chrome.runtime.sendMessage(
    {
      type: "CHAT",
      payload: {
        message: messageInput.value.trim(),
        scope: "all",
        top_k: 8,
      },
    },
    (response) => {
      if (!response?.ok) {
        setStatus(response?.error || "Chat failed", true);
        return;
      }

      answerEl.textContent = response.data?.answer_text || "";
      renderSources(response.data?.cited_sources || []);
      setStatus("Done");
    },
  );
});
