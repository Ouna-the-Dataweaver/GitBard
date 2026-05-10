import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import "../styles/v4.css";

interface IconProps {
  size?: number;
  color?: string;
}

function IconArrowLeft({ size = 18, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 12H5" />
      <path d="M12 19l-7-7 7-7" />
    </svg>
  );
}

function IconCheck({ size = 18, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function IconKey({ size = 18, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78z" />
      <path d="M15.5 7.5 19 4" />
    </svg>
  );
}

function IconWebhook({ size = 18, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 16.98h-5.99c-2.2 0-4-1.79-4-4V7" />
      <path d="M5 10 8 7l3 3" />
      <path d="M6 17h.01" />
      <path d="M10 17h.01" />
      <path d="M14 17h.01" />
      <path d="M18 17h.01" />
    </svg>
  );
}

function IconTerminal({ size = 18, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m4 17 6-6-6-6" />
      <path d="M12 19h8" />
    </svg>
  );
}

function GuideCard({
  title,
  kicker,
  children,
}: {
  title: string;
  kicker: string;
  children: ReactNode;
}) {
  return (
    <section className="v4-onboarding-card">
      <div className="v4-onboarding-card-head">
        <span>{kicker}</span>
        <h3>{title}</h3>
      </div>
      {children}
    </section>
  );
}

function Checklist({ items }: { items: string[] }) {
  return (
    <ul className="v4-onboarding-checklist">
      {items.map((item) => (
        <li key={item}>
          <IconCheck size={14} color="#34d399" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function CodeBlock({ children }: { children: ReactNode }) {
  return <pre className="v4-onboarding-code"><code>{children}</code></pre>;
}

export default function Onboarding() {
  return (
    <div className="v4-app v4-onboarding-app">
      <main className="v4-main v4-onboarding-main">
        <header className="v4-header v4-onboarding-header">
          <div>
            <div className="v4-eyebrow">Repository Onboarding</div>
            <h2>Add GitBard to a new GitLab repo</h2>
          </div>
          <Link className="v4-btn" to="/v4">
            <IconArrowLeft size={14} />
            Pipelines
          </Link>
        </header>

        <div className="v4-onboarding-scroll">
          <section className="v4-onboarding-hero">
            <div>
              <div className="v4-onboarding-label">Project checklist</div>
              <h1>Connect an existing GitLab project to the running GitBard service.</h1>
              <p>
                Use this when a repository owner wants GitBard commands in their project. The GitBard service is already deployed; the project only needs access for the bot user and a comment webhook pointing at this service.
              </p>
            </div>
            <div className="v4-onboarding-terminal" aria-label="Project-side setup summary">
              <div className="v4-onboarding-terminal-top">
                <span />
                <span />
                <span />
              </div>
              <CodeBlock>{`1. Add @nid-bugbard to the project
2. Create a project webhook
3. Select Comments events
4. Test with /oc_ask or /oc_review
5. Enable repo hook only if needed`}</CodeBlock>
            </div>
          </section>

          <section className="v4-onboarding-flow">
            <GuideCard kicker="01" title="Add the GitBard bot user">
              <div className="v4-onboarding-icon-line">
                <IconKey color="#f59e0b" />
                <p>Invite the configured GitBard account to the project, or grant access through a parent group.</p>
              </div>
              <Checklist
                items={[
                  "Add `@nid-bugbard` to the target project, or to a parent group that already covers it.",
                  "Grant at least Reporter so GitBard can read the repository, issues, merge requests, and discussions.",
                  "Use Developer only if the project’s branch or repository rules require it for clone/read access.",
                  "Confirm the bot can post comments; GitBard writes results back as project notes.",
                ]}
              />
            </GuideCard>

            <GuideCard kicker="02" title="Add the project webhook">
              <div className="v4-onboarding-icon-line">
                <IconWebhook color="#38bdf8" />
                <p>In the target GitLab project, open Settings, then Webhooks.</p>
              </div>
              <div className="v4-onboarding-table">
                <div><span>URL</span><strong>https://your-gitbard-host/webhook</strong></div>
                <div><span>Trigger</span><strong>Comments events</strong></div>
                <div><span>SSL verification</span><strong>Enable for HTTPS</strong></div>
                <div><span>Secret token</span><strong>Leave blank unless server-side validation is enabled</strong></div>
              </div>
              <p className="v4-onboarding-copy">
                GitBard only handles note webhooks. Push, pipeline, merge request, issue, and tag events are not needed for command comments.
              </p>
            </GuideCard>

            <GuideCard kicker="03" title="Check webhook delivery">
              <p className="v4-onboarding-note">
                The current webhook endpoint logs `X-Gitlab-Token` presence but does not reject invalid tokens, so the webhook secret is not an access control until validation is added.
              </p>
              <Checklist
                items={[
                  "Use GitLab’s Test button for Comments events after saving the webhook.",
                  "A successful delivery should receive a JSON response from GitBard.",
                  "If delivery fails, check project network access to the GitBard host and whether the webhook URL path ends with `/webhook`.",
                ]}
              />
            </GuideCard>

            <GuideCard kicker="04" title="Choose the command users will run">
              <p className="v4-onboarding-copy">
                Built-in commands are detected anywhere in an issue or merge request comment. Use the command that matches the project workflow, or configure a custom command in Pipeline Admin.
              </p>
              <div className="v4-onboarding-commands">
                <span>/oc_review</span>
                <span>/oc_ask</span>
                <span>/oc_test</span>
                <span>/oc_deeptest</span>
                <span>/oc_deepreview</span>
                <span>@nid-bugbard</span>
              </div>
            </GuideCard>

            <GuideCard kicker="05" title="Optional repo preparation hook">
              <p className="v4-onboarding-copy">
                If the selected pipeline enables repo preparation, GitBard runs a repo-root `.gitbard.sh` before the OpenCode preparation pass. Add this only when the project needs setup commands before review or test commands.
              </p>
              <CodeBlock>{`#!/usr/bin/env bash
set -euo pipefail

npm ci
npm test -- --runInBand`}</CodeBlock>
              <Checklist items={["Commit `.gitbard.sh` at repo root.", "Mark it executable with `chmod +x .gitbard.sh`.", "Enable repo hook in the pipeline preparation settings."]} />
            </GuideCard>

            <GuideCard kicker="06" title="Verify the connection">
              <div className="v4-onboarding-icon-line">
                <IconTerminal color="#a78bfa" />
                <p>Verify from the target project with a real issue or merge request comment.</p>
              </div>
              <CodeBlock>{`# In a GitLab MR comment
/oc_ask summarize this merge request

# For a review pipeline
/oc_review

# For a mention-triggered review
@nid-bugbard`}</CodeBlock>
            </GuideCard>
          </section>
        </div>
      </main>
    </div>
  );
}
