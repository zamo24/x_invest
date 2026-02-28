const patInput = document.getElementById("pat");
const apiBaseInput = document.getElementById("apiBase");
const saveButton = document.getElementById("save");
const status = document.getElementById("status");

async function load() {
  const { xic_pat, xic_api_base } = await chrome.storage.sync.get(["xic_pat", "xic_api_base"]);
  patInput.value = xic_pat || "";
  apiBaseInput.value = xic_api_base || "http://localhost:8000";
}

saveButton.addEventListener("click", async () => {
  await chrome.storage.sync.set({
    xic_pat: patInput.value.trim(),
    xic_api_base: apiBaseInput.value.trim() || "http://localhost:8000",
  });

  status.textContent = "Saved";
  setTimeout(() => {
    status.textContent = "";
  }, 1200);
});

void load();
