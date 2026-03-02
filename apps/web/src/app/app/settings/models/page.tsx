"use client";

import { FormEvent, useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ModelSettings } from "@/lib/types";

export default function ModelSettingsPage() {
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [inferenceMode, setInferenceMode] = useState<"hosted" | "byok">("hosted");
  const [preferredModel, setPreferredModel] = useState("");
  const [reasoningEffort, setReasoningEffort] = useState<"none" | "minimal" | "low" | "medium" | "high" | "xhigh">(
    "medium",
  );
  const [byokApiKey, setByokApiKey] = useState("");
  const [clearByokKey, setClearByokKey] = useState(false);

  async function load() {
    const response = await fetch("/api/model-settings", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load model settings.");
    }
    const payload = (await response.json()) as ModelSettings;
    setSettings(payload);
    setInferenceMode(payload.inference_mode);
    setPreferredModel(payload.preferred_model);
    setReasoningEffort(payload.reasoning_effort);
    setByokApiKey("");
    setClearByokKey(false);
  }

  useEffect(() => {
    void load()
      .catch((err) => setError(err instanceof Error ? err.message : "Unknown error"))
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch("/api/model-settings", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          inference_mode: inferenceMode,
          preferred_provider: "openai",
          preferred_model: preferredModel,
          reasoning_effort: reasoningEffort,
          byo_openai_api_key: byokApiKey.trim() || undefined,
          clear_byo_openai_api_key: clearByokKey,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error((payload as { detail?: string }).detail || "Failed to update model settings.");
      }

      setSettings(payload as ModelSettings);
      setByokApiKey("");
      setClearByokKey(false);
      setSuccess("Model settings updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <section className="space-y-6">
        <PageHeader
          title="Models"
          description="Choose hosted or BYOK model execution for Investor Copilot chat."
        />
        <Card>
          <CardContent className="pt-6 text-sm text-slate-600 dark:text-slate-300">Loading model settings...</CardContent>
        </Card>
      </section>
    );
  }

  const supportsReasoning = preferredModel.trim().toLowerCase().startsWith("gpt-5");

  return (
    <section className="space-y-6">
      <PageHeader title="Models" description="Choose hosted or BYOK model execution for Investor Copilot chat." />

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Settings update failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {success ? (
        <Alert>
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Inference Configuration</CardTitle>
          <CardDescription>
            Hosted mode uses your platform key and can be rate-limited. BYOK uses your own OpenAI key.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800 dark:text-slate-100" htmlFor="inference-mode">
                Inference mode
              </label>
              <Select
                id="inference-mode"
                value={inferenceMode}
                onChange={(event) => setInferenceMode(event.target.value as "hosted" | "byok")}
              >
                <option value="hosted">Hosted (platform key)</option>
                <option value="byok">Bring your own key</option>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800 dark:text-slate-100" htmlFor="preferred-model">
                Model
              </label>
              {inferenceMode === "hosted" ? (
                <Select id="preferred-model" value={preferredModel} onChange={(event) => setPreferredModel(event.target.value)}>
                  {(settings?.hosted_available_models || []).map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </Select>
              ) : (
                <Input
                  id="preferred-model"
                  value={preferredModel}
                  onChange={(event) => setPreferredModel(event.target.value)}
                  placeholder="e.g. gpt-5-mini"
                />
              )}
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Provider: OpenAI (MVP). Additional providers can be added next.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800 dark:text-slate-100" htmlFor="reasoning-effort">
                Reasoning effort
              </label>
              <Select
                id="reasoning-effort"
                value={reasoningEffort}
                disabled={!supportsReasoning}
                onChange={(event) =>
                  setReasoningEffort(
                    event.target.value as "none" | "minimal" | "low" | "medium" | "high" | "xhigh",
                  )
                }
              >
                {(settings?.available_reasoning_efforts || ["none", "minimal", "low", "medium", "high", "xhigh"]).map(
                  (effort) => (
                    <option key={effort} value={effort}>
                      {effort}
                    </option>
                  ),
                )}
              </Select>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Applies to GPT-5 models (including GPT-5.2). For non GPT-5 models this is ignored.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800 dark:text-slate-100" htmlFor="openai-key">
                OpenAI API key (BYOK)
              </label>
              <Input
                id="openai-key"
                type="password"
                value={byokApiKey}
                onChange={(event) => setByokApiKey(event.target.value)}
                placeholder={settings?.byo_openai_key_configured ? "Configured key is on file" : "sk-..."}
              />
              {settings?.byo_openai_key_configured ? (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Current key ends with: <code>{settings.byo_openai_key_last4}</code>
                </p>
              ) : (
                <p className="text-xs text-slate-500 dark:text-slate-400">No BYOK key is currently configured.</p>
              )}
              <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={clearByokKey}
                  onChange={(event) => setClearByokKey(event.target.checked)}
                />
                Remove existing BYOK key
              </label>
            </div>

            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save model settings"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
