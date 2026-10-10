# Shared web interface (B02 implementation boundary)

One interface for Traveller intake and confirmation, itinerary/version views, and
an Operator workspace for supplier offers, disruption injection, approval and trace.
HTTP calls use the backend's Operations gateway and operator controls. Specialist
agents are internal Python modules, not independently deployed services.

No UI or frontend framework has been implemented or selected by B01. Jason owns
B02 startup and web/database wiring; all members own their later feature screens.
