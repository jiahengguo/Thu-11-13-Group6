# Requirement and ownership mapping — B01 v1.0.0

Baseline: Stage 1 report dated September 2026, supplied locally on 10 October
2026. The current IDs are read from report sections 3 and 6 and UC-01–UC-08.
Old IDs come from `docs/Stage1_Modeling_Task_List.md` section 3. This records
semantic relationships; **no historical requirement has been renumbered**.

| Current requirement | Use cases | Agent owner | B01 boundary | Implementation cards |
| --- | --- | --- | --- | --- |
| OPS-02, OPS-AH-01 | UC-05 | Jiaheng / Operations | Case, AgentResult, TraceEvent | B06, B05, B10 |
| OPS-03, OPS-AH-01 | UC-07 | Jiaheng / Operations | TravelRequest, entitlement decision, Case | B07, B17 |
| TP-01, TP-AH-01 | UC-01 | Moore / Planning | TravelRequest, SupplierOffer, PriceBreakdown, ItineraryVersion, AgentResult | B04, B09, B13 |
| TP-02, TP-AH-01 | UC-02 | Moore / Planning | baselineVersionId, confirmedChangedFields, immutable versions | B14 |
| EXC-01, EXC-AH-01 | UC-03 | wrd / Exception | Case, AgentResult, evidence and recovery subject references | B12 |
| EXC-02, EXC-AH-02 | UC-04 | wrd / Exception | Case, AgentResult, evidence and resolution subject references | B15 |
| SUP-01, SUP-02, SUP-AH-01 | UC-06 | Jason / Supplier | SupplierOffer, PriceBreakdown, Approval | B08 |
| SUP-03, SUP-AH-02 | UC-08 | Jason / Supplier | campaign subject references, Approval, TraceEvent | B16 |
| Shared review/approval/trace (report 2.6–2.7) | All UCs | wrd; Jiaheng controls outbound delivery | ValidationResult, ReviewResult, Approval, TraceEvent | B05, B10 |

## Historical PLAN → current TP reconciliation

| Historical reference / meaning | Current relationship | Evidence | Status |
| --- | --- | --- | --- |
| PLAN-01: request and constraint collection | OPS-02/UC-05 confirmation + TP-01/UC-01 constraint interpretation | Old Stage1 task list; report 3.2.1 and 3.3.1 | Confirmed overlap; split across agents. No exact one-to-one replacement; member approval pending |
| PLAN-02: complete itinerary generation | TP-01 / UC-01 | Old task list; report 3.3.1 | Confirmed semantic match for generation; TP-01 also covers validation/comparison. Member approval pending |
| PLAN-03: comparison and modification | Comparison → TP-01 / UC-01; confirmed revision/version comparison → TP-02 / UC-02 | Old task list; report 3.3.1–3.3.2 | Confirmed split relationship; no one-to-one ID substitution. Member approval pending |
| PLAN-O1: destination/policy RAG or more real-time data | TP-O1 guidance + TP-O2 live providers; TP-O4 where forecasting is intended | Old task list; report optional features (section 4) | Partial/unresolved: older wording does not establish whether forecasting was intended |
| PLAN-AH-* | TP-AH-01 | No PLAN-AH definition found in the local Stage1 task list | Unresolved; do not create an alias or invent a source |

“Confirmed” above means the listed overlap is supported by the local documents,
not that all four members have signed off the mapping. Old task descriptions do
not establish a bijection. Final migration/alias policy requires the team's review.
TP-O3 preference learning has no identified direct PLAN counterpart. Optional
TP-O1–TP-O4 and OPS/EXC/SUP optional features are not implemented by B01.

## Reconciliation notes

- The report UC-05 now explicitly uses ExternalRequest before confirmed Case
  creation. The historical class inventory's Draft-Case conflict is resolved by
  the supplied report; v1 follows it.
- Historical CaseStatus ROUTED maps to current SM-01 ASSIGNED at the wire
  boundary. v1 selects the detailed SM-01 states; it does not silently merge the
  old candidate inventory and report state diagrams.
- PlanStatus and SM-02 assessmentState represent different lifecycles. PLANNED /
  ACTIVE membership counts must read TravelPlan facts, not FEASIBLE versions.
- Python framework and uppercase wire enums are implementation refinements;
  the report does not specify an HTTP framework or programming language.
- Rounding tie policy, final HTTP/frontend framework, and concrete database
  transaction boundaries are open decisions for B04/B02, not inferred from the
  report. Keep these decisions in the corresponding card's implementation notes.
