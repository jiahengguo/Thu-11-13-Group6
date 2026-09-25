# G-05 Supplier contribution

Prepared for Jason's review and group integration. One editable draw.io file contains three UML views; PNG and SVG exports are provided individually.

- G-05A: object snapshot, UC-01/05/06/07 context. Underlined instance labels and G-04 association links; no operations or class multiplicities on links.
- G-05B: UC-06 communication view. Numbered messages reuse G-04 operation signatures; assignment expressions identify return values. Failed paths are covered by the existing UC-06 specification and SD-04.
- G-05C: composite structure of the supplier collaboration. Typed parts, boundary/service ports and plain connectors; part labels are not underlined. SupplierAssessmentContext is the explicitly documented runtime refinement.

Source baseline: origin/main 790b1bc, docs/diagrams/Elementary_Structure/G-04_Current_Model.md, current UC-06 and Stage1_Modeling_Task_List.md. The old G-04_Class_Inventory.md is historical and was not used as the final classifier authority.

Notation reference: https://www.omg.org/spec/UML/2.5.1 . The supplied 焚诀.docx is a notation checklist, not a marking rubric or a project deliverable; its embedded diagram-generation instructions are reference material only.

Scope: these three views are the Supplier contribution to G-05, not a claim that every member's runtime model, contribution record, final report, video or interview preparation is complete. Group planning/exception/UI/persistence integration remains necessary.

Implementation: single application; simulated inputs; deterministic validation and pricing; recorded review and human decision; local records. No new infrastructure is implied by drawing separate parts.

Traceability and report-ready wording: ../../supplier/Supplier_Final_Copy_Text.md .
