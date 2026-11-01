# Customer daily planner

Traveller can load approved services in the planning form, select services across cities, set each day's start/end location, and confirm a daily meal allowance. Applying the itinerary builds the daily policy; the ordinary confirmed request and Operator review/release/adoption gates still apply. The page displays the resulting daily timeline and extra costs.

No JSON upload is required for the explicitly selected simulation mode. This mode assumes on-time travel, available venues, 20 C/no rain and 30-minute walking transfers at zero extra cost. These are customer-visible test assumptions, not measured route calculations or live forecasts. They expire 24 hours after request confirmation. Existing operator-recorded factors remain the default for manually uploaded policies. A real provider can still be injected through travel_factors.

The approved supplier catalogue must already cover the selected travel dates, cities and party size. This version does not create supplier offers or approve them, infer arbitrary city schedules, or invent missing transport. The customer selects existing services and exact daily locations. Unsupported dates, missing inventory, incompatible schedules and budget violations are blocked by the existing validators. Daily schedules use Australia/Sydney local dates.

This is a guided daily itinerary builder, not unrestricted natural-language multi-city generation. Live browser/cloud acceptance is pending.
