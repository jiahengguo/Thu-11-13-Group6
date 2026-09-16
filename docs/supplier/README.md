# Supplier Partnership Stage 1 materials

Author: Jason. These files accompany the shared Project Requirement document; the shared document remains the product authority under the Stage 1 plan.

## Requirements and specifications

- [Supplier requirements](Supplier_Requirements.md): report sections 2.5, 3.5, 4.4 and 5.4, including SUP-AH-01 and SUP-AH-02.
- [UC-06](../diagrams/Use%20case/UC-06_Source_Supplier_Inventory_and_Validate_Margin.md): SUP-01, SUP-02 and SUP-AH-01; offer assessment, pricing and approval.
- [UC-08](../diagrams/Use%20case/UC-08_Plan_Evaluate_and_Approve_a_Marketing_Campaign.md): SUP-03 and SUP-AH-02; campaign proposal, evaluation and human approval.

## Personal diagrams

All three diagrams are authored by Jason and trace to UC-06, SUP-01, SUP-02 and SUP-AH-01. They model the base supplier-offer scenario; the conditional customer quote extension is described in UC-06 A7.

- AD-04: [editable source](../diagrams/Activity_diagrams/AD-04_Activity.drawio), [image](../diagrams/Activity_diagrams/AD-04_Activity.png). Validation, pricing, review, human approval and correction routes.
- SD-04: [editable source](../diagrams/Interaction_diagrams/SD-04_Sequence.drawio), [image](../diagrams/Interaction_diagrams/SD-04_Sequence.png). Assessment messages, failure returns and approval interaction.
- SM-04: [editable source](../diagrams/State_machine_diagrams/SM-04_StateMachine.drawio), [image](../diagrams/State_machine_diagrams/SM-04_StateMachine.png). SupplierOffer business states, corrections, rejection and expiry.

## Integration and scope

- Operations owns supplier communications and external response handling under UC-05.
- UC-08 owns approved campaign/member-offer rules. UC-07 evaluates eligibility. UC-06 or purchasing validates final price and margin.
- Customer-specific discounts do not overwrite a reusable SupplierOffer base price. One fixed AUD discount per quote is sufficient for the prototype.
- Use simulated offers and costs, ordinary deterministic functions, local storage and manual retry. No real advertising, payment integration, prediction engine or background expiry service is required.
- SUP-O1 is optional and is not claimed to be implemented by the three personal diagrams.

## Remaining group integration

The group must integrate these artifacts into the final report, shared feature/use-case/class/runtime models and overall traceability and contribution records. The three personal diagrams do not complete those group tasks. Campaign data and approved member-offer rules must be represented in relevant shared models. Final shared-document changes should be reconciled with the Operations owner because UC-07 consumes those rules.
