# AI Features and API Usage

Some of pycaps' most powerful features, such as the AI-driven semantic tagger (`ai` tagger rule) and the automatic emoji effect (`emoji_in_segment`), rely on a Large Language Model (LLM) to understand the context of your script.

To use these features, you need to provide an API key. You have two options.

## Option 1: Use the Pycaps API (Recommended)

This is the default and recommended way to access AI features.

**Why use the Pycaps API?**
*   **Optimized for Pycaps**: The service is specifically tailored for pycaps' features.
*   **Generous Free Tier**: Get started for free. New accounts receive credits to process up to 5 minutes of video with AI features per month.
*   **Simplicity**: A single key manages access to all current and future AI features without needing to manage your own model infrastructure.
*   **Advanced AI usage**: Best models, optimized requests, structured output to get better results.

**It's currently under development**. It could generate unexpected responses or errors.

### How to set up:

1.  Go to `https://pycaps.com`, sign up for an account, and get your API key from the dashboard.
2.  Configure pycaps to use your key by running the following command in your terminal:

    ```bash
    pycaps config --set-api-key YOUR_PYCAPS_API_KEY
    ```

This will store your key locally for all future `pycaps` runs.

## Option 2: Use Your Own OpenAI API Key

If you prefer to use your own OpenAI account and billing, you can provide your own API key. Pycaps will use this key as a fallback if a Pycaps API key is not configured. In these cases, the default prompts coded in the library will be used to request the LLM. These prompts are not optimized, but they do their job.

### How to set up:

You must set an environment variable named `PYCAPS_OPENAI_API_KEY`.

**On macOS/Linux:**
```bash
export PYCAPS_OPENAI_API_KEY="sk-YourOpenAIKeyHere"
```
You can add this line to your shell profile (e.g., `~/.zshrc`, `~/.bash_profile`) to make it permanent.

**On Windows (Command Prompt):**
```powershell
setx PYCAPS_OPENAI_API_KEY "sk-YourOpenAIKeyHere"
```
You may need to restart your terminal for the change to take effect.

## How Pycaps Prioritizes Keys

When an AI feature is used, pycaps checks for keys in the following order:

1.  It first looks for a key set via the `pycaps config --set-api-key` command (the **Pycaps API** key).
2.  If that is not found, it then checks for the `PYCAPS_OPENAI_API_KEY` environment variable (your **own OpenAI key**).
3.  If neither is found, AI-dependent features will be disabled, and a warning will be logged.
