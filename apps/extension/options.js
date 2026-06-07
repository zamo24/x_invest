const patInput = document.getElementById("pat");
const apiBaseInput = document.getElementById("apiBase");
const saveButton = document.getElementById("save");
const testButton = document.getElementById("test");
const status = document.getElementById("status");
const settingsCore = globalThis.XicSettingsCore;

function setStatus(message, type = "") {
  status.textContent = message;
  status.className = type;
}

async function requestApiPermission(apiBase) {
  const origin = settingsCore.permissionOrigin(apiBase);
  const alreadyGranted = await chrome.permissions.contains({ origins: [origin] });
  if (alreadyGranted) {
    return;
  }
  const granted = await chrome.permissions.request({ origins: [origin] });
  if (!granted) {
    throw new Error("API origin permission was not granted.");
  }
}

async function validatedInput() {
  const pat = settingsCore.validatePat(patInput.value);
  const apiBase = settingsCore.normalizeApiBase(apiBaseInput.value);
  await requestApiPermission(apiBase);
  return { pat, apiBase };
}

async function removeObsoletePermission(previousApiBase, nextApiBase) {
  if (!previousApiBase || settingsCore.normalizeApiBase(previousApiBase) === nextApiBase) {
    return;
  }
  const previousUrl = new URL(settingsCore.normalizeApiBase(previousApiBase));
  if (previousUrl.protocol === "https:") {
    await chrome.permissions.remove({ origins: [settingsCore.permissionOrigin(previousApiBase)] });
  }
}

async function load() {
  const settings = await settingsCore.readSettings();
  patInput.value = settings.pat;
  apiBaseInput.value = settings.apiBase;
}

saveButton.addEventListener("click", async () => {
  setStatus("Saving...");
  try {
    const previousSettings = await settingsCore.readSettings();
    const settings = await validatedInput();
    await settingsCore.saveSettings(settings);
    await removeObsoletePermission(previousSettings.apiBase, settings.apiBase);
    apiBaseInput.value = settings.apiBase;
    setStatus("Settings saved locally.", "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error), "error");
  }
});

testButton.addEventListener("click", async () => {
  setStatus("Testing connection...");
  try {
    const settings = await validatedInput();
    const response = await chrome.runtime.sendMessage({
      type: "TEST_CONNECTION",
      payload: { pat: settings.pat, api_base: settings.apiBase },
    });
    if (!response?.ok) {
      throw new Error(response?.error || "Connection test failed.");
    }
    setStatus(`Connected as ${response.data?.email || response.data?.user_id || "authenticated user"}.`, "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error), "error");
  }
});

void load().catch((error) => {
  setStatus(error instanceof Error ? error.message : String(error), "error");
});
