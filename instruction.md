# Integrating an AI Code Reviewer into GitLab (Step-by-Step Guide)

**Overview:** By early 2026, AI-assisted code review is becoming common (GitLab's own "Duo" offers AI code review in higher tiers). For a self-hosted GitLab CE instance, you can integrate your own AI (using your preferred LLM provider) to review Merge Requests (MRs) on demand. The idea is to use GitLab's APIs or webhooks to fetch MR changes, have an AI analyze them, and then post feedback as MR comments. Below is a step-by-step guide to set this up, focusing first on manual summoning (triggering the AI with a comment), with notes on automating reviews for every MR. The solution will use a GitLab webhook and a custom script (mostly Python, as requested) to call your AI model. We assume you already have an AI API (a "GLM coding plan") configured and ready to use.

## Step 1: Prepare Your AI Access and GitLab Credentials

**AI API Access:** Ensure you have the API endpoint and key for your AI model provider ready (we'll use it to send code for review). Since you mentioned an "OpenCode" provider with unlimited usage, we'll assume this is configured. No need to focus on this – just have the credentials handy in your script or environment.

**GitLab Token / Bot User:** Set up a way for your script to authenticate to GitLab so it can read MR data and post comments. The simplest is to create a Personal Access Token (PAT) with `api` scope on your GitLab account (or a dedicated "AI bot" account). You can also create a Project Access Token or Group Access Token with Developer permissions and API scope. Save this token – the script will use it to call GitLab's REST API. (Using a dedicated token named e.g. "AI Code Reviewer" is nice because comments posted by the AI can be attributed to that name.)

**GitLab Runner (optional):** You mentioned having a machine for GitLab Runner. This is useful if you decide to run the AI review as part of CI pipelines. For the manual trigger approach, we'll instead run a persistent service (or a lightweight server) to handle webhooks, but you could use the runner to trigger a job as well (more on that later).

## Step 2: Set Up a Webhook in GitLab

To allow GitLab to "ping" your AI whenever needed, configure a webhook:

1. **Create Webhook:** In your GitLab project, go to **Settings > Webhooks** (in older GitLab UI, Settings > Integrations). Click **Add Webhook**.
2. **URL:** Enter the URL where your AI review service will listen. If you're running the script on a server, this could be an HTTP URL to that server. (For testing, you could use a tool like ngrok to expose a local server, but in a company setup you might deploy this service internally and use an internal URL.)
3. **Trigger Events:** Select:
   - **Merge Requests events:** so that the webhook fires when MRs are created or updated (for automatic reviews).
   - **Comments (Note) events:** so that the webhook fires when someone comments on an MR (for manual trigger on a special command). Enabling the "Comment" event will let us trigger the AI on-demand by posting a certain comment on the MR.
4. **Secret Token (optional):** You can set a secret token in the webhook settings. If set, your service can verify incoming webhook payloads by comparing the token.
5. **Custom Headers (if needed):** GitLab allows adding custom HTTP headers in the webhook config. If your AI service expects any API keys in headers, you can configure them here. For example, a third-party service like CRken (an AI code review tool) requires setting API keys in headers when configuring the webhook. In our custom setup, you might not need this, since our script will have the AI key. But you will use the GitLab token in the script to call back to GitLab (not as a webhook header).
6. **Save the Webhook.** Now GitLab will send a POST request to your service for the selected events.

*Example: Configuring a GitLab project webhook to trigger on Merge Request and Comment events (you would put your service's URL and any required headers or secret).*

## Step 3: Implement the Webhook Handler Service (AI Review Script)

Next, create a script or small web service to handle the webhook calls and interface with the AI. Here's a breakdown of what it should do:

**Choose a Platform:** You can write this in Python using a web framework like Flask or FastAPI, which makes it easy to receive JSON POST requests. Alternatively, a Node.js script or any language you prefer is fine – but since you're comfortable with Python, we'll assume that.

**Webhook Endpoint:** Set up an endpoint (e.g. `/gitlab-webhook`) that accepts POST requests. GitLab will send a JSON payload describing the event. Your service should parse this JSON.

**Event Parsing:** Determine the event type. In the JSON payload, there's an `"object_kind"` field. For a merge request event it will be `"merge_request"`, and for a comment it will be `"note"` (note = comment). Also check the `"event_type"` or other fields to differentiate MR opened/updated vs. a comment on an MR.

**Manual trigger via comment:** If the event is a note (comment), and the comment is on a Merge Request, inspect the comment text (payload will have something like `object_attributes.note` containing the text). Decide on a trigger phrase that users will type to summon the AI. For example, you could use a slash command like `/ai-review` or `/chatgpt`. If the comment text matches that trigger (e.g. starts with `/ai-review`), you proceed to do the AI review. If it's any other comment, ignore it. (This prevents the AI from responding to every comment, and only reacts when summoned explicitly.)

*Tip:* The trigger word can be anything unique. In the CRken tool, for instance, the default trigger is a comment containing "/crken", and the system only reacts to comments with that keyword. You could similarly choose `/ai-review` or even an @ mention of a bot user (if you created an AI user and added it to the project, mentioning it might be a natural trigger).

**Auto trigger on MR events:** If the event is a `merge_request` and, say, `"state":"opened"` (or the payload might have an action like "open" or "update"), you can automatically trigger the AI review without waiting for a comment. For now, if you want manual only, you might ignore these. But we'll revisit auto reviews in Step 6.

**Gather MR Data:** Once you've decided to run a review (either manual trigger detected, or auto on MR open), your script needs the code changes from the MR:

- Use GitLab's API to fetch the MR changes (the diff). GitLab provides an endpoint specifically for this: **Merge Request Changes API**. For example:

  ```
  GET /api/v4/projects/<project_id>/merge_requests/<mr_iid>/changes?access_raw_diffs=true
  ```

  This returns the list of changed files and diff hunks in the MR. By adding `access_raw_diffs=true`, you can get raw diff text in the response. Your script can call this (e.g. with Python's `requests` library), including an `Authorization: Bearer <your_token>` header or `PRIVATE-TOKEN: <your_token>` header for auth.

- *(Optionally, you can also retrieve existing notes on the MR using the Merge Request Notes API – `GET /projects/<id>/merge_requests/<iid>/notes` – if you want the AI to see previous human comments or to avoid repeating suggestions. This is more relevant if doing iterative reviews; for a simple first pass, you can skip fetching existing notes or just fetch them to include in prompt context.)*

- *Using environment variables in CI:* If you were running this in a GitLab CI job instead of a webhook service, GitLab provides environment vars like `$CI_PROJECT_ID` and `$CI_MERGE_REQUEST_IID` for the MR being pipelined. In a webhook, you'll get those IDs from the JSON (e.g. `project.id` and `merge_request.iid` fields).

**Compose the Prompt for AI:** Now prepare a prompt to send to your LLM. This is crucial to get useful output. For example, you might create a prompt like:

> "You are an AI code reviewer. I will provide a git diff from a Merge Request. Please analyze the changes and provide a code review: find potential bugs, security issues, code style problems, or any suggestions for improvement. Be concise and specific in your feedback, and if you see any sensitive information (like passwords or keys), point it out."

Then append the code diff (or the relevant portions) to this prompt. If the diff is very large, you may need to summarize or truncate parts of it (especially if your model has input length limits). Since you mentioned mostly Python and a bit of JS/HTML, those diffs might be reasonably sized. For very large diffs, one strategy is to split by file and have the AI analyze file by file, but that adds complexity. Start simple: include the full diff text if possible. Ensure the diff is formatted in a readable way. The model can understand code or diff syntax, but you might strip out unneeded lines. If you fetched existing MR comments, you could also prepend them in the prompt as "Previous discussion/comments:" so that the AI doesn't repeat what's already been noted. This is an advanced tweak – initially, you can just focus on the code changes themselves.

**Call the AI API:** Using your AI provider's SDK or HTTP API, send the prompt and receive the completion. For example, if using OpenAI's API, you'd call the chat completion endpoint with the prompt. Since cost is not an issue for you, you might use a strong model (e.g. GPT-4 or similar) for better analysis. Ensure your script handles the response and any errors (e.g. network issues or model errors).

**Parse AI Response:** The AI will return some text which is the review. You might want to do minimal processing on it – e.g., ensure it's Markdown formatted (most LLMs will format bullet points or code suggestions nicely if asked).

## Step 4: Post the AI's Review as a GitLab Comment

Finally, take the AI-generated review and post it back to the Merge Request as a comment:

- Use the GitLab POST API for MR comments: **Create Merge Request Note**. The endpoint is:

  ```
  POST /api/v4/projects/<project_id>/merge_requests/<mr_iid>/notes
  ```

  with JSON body containing `"body": "<your comment text>"`. Authenticate this request with the PAT or token you set up (e.g. using an HTTP header `PRIVATE-TOKEN: <token>`). This will create a new comment on the MR.

- In the comment text, you might want to prefix it with something like "**🤖 AI Reviewer:**" to make it clear this is an automated review. This is optional, but helps distinguish AI feedback from human comments.

- **Formatting:** If the AI mentioned specific lines or code, GitLab's Markdown supports syntax highlighting and also linking to lines in diffs, but initially just posting plain text or simple lists is fine. The AI's response might already be in bullet form or paragraphs. Ensure the content is not too long – if it's extremely lengthy, consider trimming less important parts before posting to avoid overwhelming the MR.

Once posted, anyone viewing the MR will see the comment. Because we used your token, it will appear as authored by the token's user. (If you used a Project Access Token named "AI Reviewer", it will show up as a bot with that name, which is nice.)

*Technical note:* Creating a comment via API is straightforward. For example, using Python's `requests` library:

```python
import requests

url = f"https://gitlab.yourdomain.com/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
data = {"body": ai_review_text}
requests.post(url, headers=headers, json=data)
```

This assumes `project_id` and `mr_iid` are known (from the webhook payload), and `ai_review_text` is the string from the AI.

## Step 5: Test the Workflow (Manual Trigger in MR)

With everything set up, perform a dry run:

1. **Open or create a Merge Request** in your GitLab with some changes (it can be a dummy change in a test repo to start).
2. **Summon the AI:** Add a comment on the MR with the trigger phrase, e.g. `/ai-review please`. Once you post this, GitLab will send the webhook to your service (because we enabled Comments events).
3. **Observe the Service:** Your script should log or print what it's doing (it's helpful to log events in the handler). It should detect the trigger, fetch the MR diff, call the AI, and then post a comment. This might take some seconds depending on the model's response time.
4. **Check the MR:** Refresh the Merge Request page and you should see a new comment from the AI (or from the user whose token you used). It will contain the AI's analysis. 🎉

For example, the AI might say something like: "**AI Reviewer:** I see that you've hardcoded a password in config.json – this is a security risk (please use env variables). Also, function `foo()` lacks error handling for null inputs, consider adding checks." If your model is powerful (and your prompt well-crafted), the feedback can be quite insightful. In one real-case example, an AI noticed a JSON file with plaintext passwords and commented with a warning, even masking the sensitive info and tagging the author. Don't be surprised if the AI catches things human reviewers might miss – that's the benefit of using an LLM for this task.

**Iterate if needed:** You might need to adjust the prompt or how you format the diff if the output isn't satisfactory. For instance, if the AI gave too verbose an answer, you could ask it to be more concise. Or if it missed an obvious issue, consider improving the prompt or using a larger model. This tuning is part of the process.
