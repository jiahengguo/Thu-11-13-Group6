# TripMate AI - Four-Page Project Requirement Outline

This is the recommended structure for the **Project Requirement Documentation**. It intentionally follows the scale and role-based organisation of the official four-page Project Requirement Example.

Target length: approximately **four pages in Word**, excluding an optional cover page.

Do not place the full UML/model set in this document. Feature, Use Case, Class, Activity, Interaction, State Machine, and other diagrams belong to the wider Stage 1 report and should be based on this requirement baseline.

---

# Suggested page allocation

| Page | Main content | Approximate space |
| --- | --- | --- |
| Page 1 | Application introduction; Primary Users and Roles | 1 page |
| Page 2 | Core Features for Travellers; Operations Agent | 1 page |
| Page 3 | Core Features for Travel Planning, Customer Exception, and Supplier Partnership Agents | 1 page |
| Page 4 | Human Operator; Optional Features; Project Notes and Contributions | 1 page |

---

# TripMate AI: One-Person AI Travel Company

## 1. Application introduction

Write two or three concise paragraphs covering:

- The real problem: travel planning information is fragmented across transport, accommodation, activities, weather, prices, and policies.
- The proposed solution: TripMate AI is an LLM-powered multi-Agent travel service supervised by one human founder/operator.
- The application domain: Smart Personal Assistant and One-Person AI Company.
- The main difference from a normal itinerary chatbot: specialised business Agents collaborate, use tools, validate results, handle later disruptions and complaints, and support a commercial business model.
- The prototype boundary: Australian domestic short trips using simulated supplier, booking, payment, and disruption data.

Suggested final sentence:

> TripMate AI aims to determine whether one human operator can provide a trustworthy and commercially plausible travel service with the support of specialised LLM-powered Agents, deterministic tools, and risk-based human oversight.

## 2. Primary users and roles

Introduce the main users and roles in one short paragraph, followed by concise bullets.

### 2.1 Travellers

- Submit travel goals, dates, budgets, preferences, and hard constraints.
- Compare valid travel plans and request revisions.
- Recheck active trips after weather, cancellation, strike, or other disruptions.
- Submit complaints and request human review.
- Use either a free or paid membership tier.

### 2.2 Operations Agent

- Combines customer acquisition, marketing support, and customer front-desk service.
- Tracks Leads and Campaign results.
- Recognises customer intent and collects missing information.
- Checks membership entitlements and routes Cases to the correct Agent.

### 2.3 Travel Planning Agent

- Combines transport and itinerary planning in one role.
- Searches and combines transport, accommodation, and activities.
- Applies hard constraints and preference modes.
- Produces complete plans, alternatives, explanations, and revised versions.

### 2.4 Customer Exception Agent

- Combines disruption recovery and complaint handling in one role.
- Identifies affected itinerary items and proposes recovery options.
- Investigates complaints using orders, evidence, supplier terms, and company policy.
- Escalates high-risk or low-confidence Cases to the human operator.

### 2.5 Supplier Partnership Agent

- Connects the company with large tourism suppliers.
- Imports simulated supplier inventory, prices, availability, and terms.
- Compares supplier offers and calculates expected commission or margin.
- Escalates unusual terms, stale inventory, or out-of-policy margins.

### 2.6 Human founder/operator

- Supervises all AI roles and remains responsible for the company.
- Reviews high-risk, financial, contractual, legal, safety, and low-confidence Cases.
- Approves or rejects external publication, supplier commitments, and compensation proposals.

### 2.7 Reviewer/Guardrail

Describe Reviewer/Guardrail briefly as a supporting control component, not another customer-facing company department:

- Checks constraints, arithmetic, schedule conflicts, evidence, policies, confidence, membership rules, prices, margins, and authorisation.

Conclude the section with one sentence explaining that the four business Agents collaborate under the supervision of the human founder/operator.

## 3. Key capabilities and core features

Follow the Example's pattern: organise Core Features by user or Agent role rather than presenting a long software-requirement table.

### 3.1 For travellers

#### Travel request and consultation feature

- Accept a natural-language travel request.
- Extract route, dates, budget, party size, preferences, baggage, accessibility, and other hard constraints.
- Ask the user to confirm or correct missing information before planning.

#### Travel planning and comparison feature

- Generate complete transport, accommodation, and activity plans.
- Apply every hard constraint before scoring or recommendation.
- Support Comfort, Value, and Budget modes.
- Show a recommendation, eligible alternatives, total price, sources, timestamps, trade-offs, and exclusion reasons.

#### Active-trip recheck feature

- Recheck current transport, weather, disruption, and venue information.
- Identify invalid itinerary items and generate checked alternatives.
- Preserve the original itinerary and create a new version only after customer confirmation.

#### Complaint and human-review feature

- Link the complaint to the relevant order, quote, itinerary versions, supplier terms, evidence, and Agent Trace.
- Show the proposed resolution and escalate high-risk Cases for operator approval.

#### Membership feature

- Free members may hold no more than two simultaneous planned or active trips.
- A free-member trip may cover no more than five days.
- Free members may see clearly labelled advertising.
- Paid members are not subject to the free-tier trip-count and duration limits.
- Paid members receive an ad-free experience, route-map visualisation, and approved premium features.
- Advertising must not change hard-constraint filtering or recommendation ranking.

### 3.2 For the Operations Agent

#### Customer acquisition and Campaign feature

- Analyse simulated audiences and channel-performance data.
- Draft advertising content and Campaign recommendations.
- Track Leads, acquisition cost, and conversion.
- Require operator approval before real publication or spending.

#### Customer front-desk feature

- Identify intent, answer routine questions, collect missing information, and route planning or exception Cases.
- Check membership limits before a new trip is created or extended.

### 3.3 For the Travel Planning Agent

#### Complete itinerary feature

- Retrieve eligible transport, accommodation, and activity resources.
- Combine them into complete itinerary candidates.
- Use deterministic tools to check budget, schedule, transfer time, and other constraints.
- Explain and revise valid plans without silently relaxing customer requirements.

### 3.4 For the Customer Exception Agent

#### Disruption recovery feature

- Match current disruption events to active itineraries.
- Re-plan only affected future items.
- Recheck incremental cost, remaining budget, timing, safety, and conflicts.

#### Complaint resolution feature

- Classify severity and gather relevant evidence.
- Check company and supplier policy.
- Propose a resolution and request human approval where required.
- Preserve Case status and allow a resolved complaint to be reopened.

### 3.5 For the Supplier Partnership Agent

#### Supplier-resource feature

- Import and normalise simulated supplier offers.
- Preserve source, timestamp, availability, price, cancellation terms, and reliability information.
- Prevent stale or invalid offers from entering customer recommendations.

#### Pricing and margin feature

- Record supplier cost separately from customer price.
- Calculate fees, commission or markup, and expected gross margin deterministically.
- Require operator review when commercial terms or margins are outside policy.

### 3.6 For the human founder/operator

#### Company oversight feature

- View prioritised Cases, pending approvals, Agent/Tool Traces, operating cost, supplier margin, membership information, and Campaign performance.
- Approve, edit, or reject high-risk Agent proposals.
- Retain final responsibility for financial, contractual, legal, safety, and external actions.

## 4. Optional features

Keep this section short. List optional features by role, as in the Example.

### 4.1 For travellers

- Multilingual or voice interaction.
- Proactive disruption notifications.
- Long-term preference memory with customer consent.

### 4.2 For the Operations Agent

- Advanced demand forecasting and customer-retention analysis.
- Automated Campaign experiment recommendations.

### 4.3 For the Travel Planning Agent

- RAG for destination and travel-policy knowledge.
- Real external travel-data integration beyond the controlled prototype dataset.

### 4.4 For the Supplier Partnership Agent

- Supplier reliability scorecards.
- Demand-based inventory and partnership recommendations.

### 4.5 For the Customer Exception Agent

- Proactive anomaly prediction before a disruption affects the itinerary.

## 5. Project notes

Finish with a short “Please Note” section similar to the Example:

- TripMate AI implements a One-Person AI Company with one human founder/operator and four clearly differentiated AI business roles.
- The Agents collaborate, use external or simulated tools, and adapt their actions based on results.
- The project should demonstrate a meaningful improvement over a single travel chatbot and make appropriate use of LLM strengths.
- The prototype uses simulated bookings, payments, refunds, supplier contracts, and advertising expenditure.
- Safety, legal, contractual, high-value financial, and low-confidence decisions remain subject to human approval.
- Each of the four group members must be clearly assigned at least two Core Features and one Optional Feature.
- Individual contributions must be identified in the Stage 1 submission.

## 6. Four-member feature allocation

Include this compact table at the end or in the Stage 1 contribution section. Replace Member A-D with real names.

| Member | Main business area | Core Features - at least 2 | Optional Feature - at least 1 |
| --- | --- | --- | --- |
| Member A | Operations and membership | Customer front desk; membership entitlement; Campaign/Lead handling | Demand or retention analysis |
| Member B | Travel planning | Complete itinerary; hard-constraint validation; preference comparison | Destination/policy RAG |
| Member C | Customer exceptions | Disruption recovery; complaint resolution; human escalation | Proactive anomaly prediction |
| Member D | Supplier and profitability | Supplier-offer management; price/margin calculation; commercial validation | Supplier reliability scorecard |

---

# What should not be expanded inside the four-page requirement document

Keep the following items in the wider Stage 1 report or internal task document:

- Full FR/NFR catalogue.
- Detailed Use Case Specifications.
- Ad hoc requirements written by each student.
- Feature and Overall Use Case Diagrams.
- Class, Object, Collaboration, and Structured Class Diagrams.
- Activity, Interaction, and State Machine Diagrams.
- Architecture, Package, and Deployment Diagrams.
- Complete data dictionary and tool contracts.
- Full traceability and change-management matrices.

The four-page requirement document only needs to establish the application, users, roles, Core Features, Optional Features, and important project constraints clearly enough for all later models to use as a consistent baseline.
