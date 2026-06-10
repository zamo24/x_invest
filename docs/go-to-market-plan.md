# Go-To-Market Plan

This plan covers the first 90 days of customer acquisition for X Investor Copilot. It prioritizes learning, activation,
and retention before broad distribution or paid advertising.

## Implementation Status

Repository launch assets currently implemented:

- Benefit-led public homepage and private beta call to action.
- Configurable beta application form destination.
- Draft privacy policy, Chrome Limited Use disclosure, terms, and investment-advice disclaimer.
- Public support-contact configuration.
- Public-page browser tests.

Required external actions before recruitment:

- Configure `NEXT_PUBLIC_BETA_APPLICATION_URL` and `NEXT_PUBLIC_SUPPORT_EMAIL`.
- Have qualified counsel review the draft privacy policy and terms.
- Record the product demo and prepare the Chrome Web Store listing.
- Select and configure privacy-conscious product analytics using the event taxonomy below.
- Begin the founder-led outreach and interview cadence after the launch-readiness gate is met.

## Positioning

Primary promise:

> Never lose an investment thesis. Save valuable research from X, organize it, and ask source-cited questions later.

X Investor Copilot is a personal research memory for active retail investors. It is not a stock picker, trading signal,
or source of investment advice.

### Ideal Customer Profile

The initial customer:

- Is an active retail investor who uses X several times per week for research.
- Saves at least 20 investment-related tweets, threads, or articles each month.
- Currently relies on bookmarks, notes, screenshots, browser tabs, or memory.
- Regularly struggles to find an old thesis, source, or update.
- Values source traceability and is willing to pay for a better research workflow.

Do not initially optimize for investment firms, casual investors, or users primarily seeking stock recommendations.

### Core Demonstration

Every demo and onboarding session should show this workflow:

1. Save an investment thread from X.
2. Organize it into a research folder.
3. Ask a question across the saved research and receive source citations.
4. Revisit an older immutable thread snapshot.

## Offer

Run a six-week, invitation-based concierge beta. Personally onboard each user and provide direct support in exchange for
regular product feedback.

After users experience the core value, offer:

> **Founding Investor Plan: $19/month, price locked for the first 12 months.**

The founding plan includes organization, thread snapshots, source-cited chat, and direct founder support, subject to
reasonable usage limits. Do not offer permanent free usage during this validation period.

## Launch Readiness: Weeks 1-2

Complete these prerequisites before actively recruiting beta users:

- Replace technical homepage copy with the primary promise, workflow, and beta application call to action.
- Record a 60-90 second product demo covering the core demonstration.
- Add a beta application form that asks about investing style, X usage, current workflow, and primary pain point.
- Publish a privacy policy, terms of service, Chrome Limited Use disclosure, support contact, and clear
  "not investment advice" disclaimer.
- Prepare the Chrome Web Store listing, screenshots, permission explanations, and privacy disclosures.
- Add privacy-conscious analytics that do not record saved source content, chat text, PATs, or API keys.

Track these funnel events:

```text
beta_application_submitted
account_created
extension_connected
first_source_saved
ten_sources_saved
first_chat_completed
week_one_return
subscription_started
```

Before recruitment begins, five test users must independently complete account creation, extension setup, first save,
and first source-cited chat within 15 minutes.

## Concierge Beta: Weeks 3-8

Recruit 30 active retail investors through:

- Personal X relationships and targeted direct messages.
- Helpful replies to investors discussing research organization or lost-source problems.
- Two weekly X posts demonstrating real research workflows.
- Investor Discords, subreddits, newsletters, and communities where promotion is permitted.
- Referrals from activated beta users.

With 5-10 marketing hours available each week, use this cadence:

| Activity | Weekly Target |
|---|---:|
| Personalized outreach messages | 20-25 |
| Workflow demonstrations or educational X posts | 2 |
| Onboarding or feedback calls | 3 |
| Funnel and feedback review | 1 |
| Highest-impact onboarding or retention improvement | 1 |

### Outreach Message

Use this as a starting point and personalize the opening sentence:

> I built a tool for investors who save valuable X threads and then cannot find them later. It lets you save tweets,
> threads, and articles, then ask source-cited questions across your personal research library. I am onboarding a small
> free beta cohort and would value feedback from someone who actively researches on X. Interested in a 15-minute
> walkthrough?

Do not mass-message users or lead with generic AI claims. Reference a real part of the recipient's research workflow.

### Onboarding Session

Each onboarding session should:

1. Ask the user to describe their existing X research workflow.
2. Install and connect the extension.
3. Have the user save three real sources.
4. Create one folder matching an active investment theme.
5. Ask one real research question and inspect its citations.
6. Schedule a 15-minute follow-up seven days later.

### Activation Definition

A user is activated when they complete all of the following within seven days:

- Connect the extension.
- Save at least ten sources.
- Create or use a research folder.
- Complete at least three source-grounded chats.
- Return on a separate day.

### Customer Interview Guide

Ask behavior-focused questions:

1. Before using this product, how did you save and revisit research from X?
2. Tell me about the last time you could not find an investment source you remembered.
3. Which saved source or answer was most useful this week, and why?
4. What felt confusing or took too long?
5. What did you expect the product to do that it could not do?
6. What would make you stop using it?
7. How disappointed would you be if you could no longer use it?
8. What would make the product worth paying for every month?

Do not rely on whether users say they like the product. Prioritize observed usage, repeated pain, and demonstrated value.

## Monetization: Weeks 9-12

Offer the founding plan only to activated users. Explain that the beta is transitioning to a paid product and that their
founding price is locked for 12 months.

- Use a hosted subscription checkout rather than building complex billing infrastructure.
- Personally follow up with users who do not convert to understand the objection.
- Ask paying users for permission before using testimonials or results publicly.
- Offer one free month for each referred user who activates, capped at three free months.
- Delay Product Hunt and broad public launches until onboarding is self-serve and the extension is publicly distributed.
- Do not spend meaningfully on paid acquisition until retention and paid conversion targets are met.

### Testimonial Consent

Obtain explicit written permission before publishing a testimonial. Confirm the exact quote, name/title attribution, and
whether any incentive was provided. Testimonials must describe the user's real experience and must not imply investment
performance or guaranteed outcomes.

## Scorecard And Decision Gates

Track the funnel weekly in a simple spreadsheet or analytics dashboard:

| Metric | 90-Day Target |
|---|---:|
| Targeted prospects contacted | 150 |
| Beta users onboarded | 30 |
| Seven-day activation rate | 60%+ |
| Week-four retained users | 35%+ |
| Activated-to-paid conversion | 30%+ |
| Founding paid customers | 10+ |
| Usable testimonials or case studies | 5 |

Apply these decision rules:

- If activation is below 40% after 15 onboarded users, pause acquisition and fix onboarding.
- If week-four retention is below 25%, revisit the core workflow and customer segment before adding features.
- If users retain but do not pay, test messaging, offer presentation, and price before assuming the product lacks value.
- Begin broader organic launches only after reaching at least 10 paying customers and 35% week-four retention.
- Test paid acquisition only after onboarding conversion and expected customer lifetime value can support it.

## Weekly Operating Review

Maintain one row per experiment:

| Week | Hypothesis | Action | Metric | Result | Decision |
|---|---|---|---|---|---|
| Example | A guided install will improve activation | Run three live onboardings | Seven-day activation | Pending | Continue, change, or stop |

At the end of each week:

1. Update the scorecard.
2. Review every user who failed to activate or return.
3. Categorize feedback into onboarding, reliability, missing workflow, trust, and willingness-to-pay issues.
4. Choose one acquisition experiment and one product improvement for the next week.
5. Record the result and decision before starting another experiment.

## Marketing Budget

Keep monthly spending under $500 during validation:

- Use free or inexpensive form, scheduling, email, and analytics tools.
- Spend only on assets or small community/creator experiments that directly reach the ideal customer profile.
- Do not buy broad ads, followers, email lists, or generic sponsorships.

## Messaging And Compliance Guardrails

- Describe the product as research organization and source-cited retrieval.
- Do not promise better returns, winning trades, or improved investment performance.
- Clearly state that the product does not provide investment advice.
- Explain what user data is stored and how it is used.
- Keep Chrome extension permissions narrow and disclosures accurate.
- Do not publish customer names, saved research, chat content, or outcomes without explicit consent.

Relevant references:

- [Chrome Web Store User Data Policy](https://developer.chrome.com/docs/webstore/user_data)
- [Chrome Web Store Program Policies](https://developer.chrome.com/docs/webstore/program-policies/policies)
- [FTC endorsement guidance](https://www.ftc.gov/news-events/topics/truth-advertising/advertisement-endorsements)
