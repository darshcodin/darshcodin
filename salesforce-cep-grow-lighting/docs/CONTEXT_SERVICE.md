# Context Service + context-hydrated Expression Set

Built per the solution design's Layer 3 (Calculation services: **Context Service** input
assembly → **Business Rules Engine** expression set). Status: the assets are built and the
Context Service runs; invoking the expression set to replace the before-save flow is gated on
one Designer-set binding (below).

## What was built

| Component | API name | Status |
|---|---|---|
| Context Definition | `GrowLightingContext` | ✅ deployed (API v63) |
| Context-hydrated Expression Set | `Grow_Lighting_MN_Context_Calc` (V1) | ✅ deployed & Active |

- **`GrowLightingContext`** — the Context Service input-assembly graph. Root node
  `GrowLightingLine` → `IndividualApplicationItem`, with input attributes `FixtureQuantity`,
  `RoomType`, `ProposedPPF`, `ProposedWatts`, `DLCTier`, `InvoiceDate`, each hydrated from the
  line's fields (`Fixture_Quantity__c`, `Market_Segment_Room_Type__c`, …).
  *(ContextDefinition requires API v63; the project is pinned to 63.0.)*
- **`Grow_Lighting_MN_Context_Calc`** — an Expression Set that declares
  `<contextDefinitions>GrowLightingContext</contextDefinitions>`, so its inputs are hydrated by
  the Context Service rather than hand-passed. Same 7-output calculation as the variable-based
  `Grow_Lighting_MN_Calculator`.

## The Context Service runs — verified
The Context Service is the standard **`buildContext`** invocable action. Called with the
`GrowLightingContext` definition id and a line, it hydrates the graph and returns a live
`contextId`:

```bash
sf api request rest "/services/data/v63.0/actions/standard/buildContext" --method POST --target-org cep \
  --body '{"inputs":[{"contextDefinitionId":"<GrowLightingContext id>","contextData":"{\"IndividualApplicationItem\":[{\"id\":\"<lineId>\"}]}"}]}'
# -> outputValues.contextId = "r000000...."   (context hydrated)
```
Companion Context Service actions present: `persistContextData`, `queryContextTags`,
`updateContextAttributes`, `deleteContextCache`.

## The engine runner — found
Expression sets **are** invocable in this org via the standard **`invokeRule`** action
(this is the runtime the earlier Connect-REST/Apex search couldn't find):
```
invokeRule( ExpressionSet = <api name>, Parameters = <List of { variableName: value }> )
```
Confirmed: `invokeRule` accepts `ExpressionSet` + a **List** `Parameters` and executes the set.

## The one remaining gap (Designer-set)
`invokeRule` rejects the inputs with *"the flow doesn't have a variable with the name 'Qty', or
the variable isn't available for input."* — for **both** the variable-based and context-based
sets, even though the deployed versions carry `<input>true</input>` on every input variable.
So `<input>true</input>` in metadata is **not** sufficient to expose a variable to `invokeRule`;
that exposure is set when the set is authored/run in the **Expression Set Builder** and isn't
captured by the metadata we can hand-author (the same Designer-gated pattern as the Decision
Matrix lookup step).

### To finish (one Designer step, then I wire it)
1. Open `Grow_Lighting_MN_Context_Calc` in the **Expression Set Builder**, map its inputs to the
   `GrowLightingContext` node attributes (or mark the input variables available for input), and
   save/activate.
2. Then it runs end to end: **`buildContext`** (hydrate) → **`invokeRule`** (evaluate), which a
   record-triggered flow can call on line submit — replacing the before-save formula block.
3. Until then, the **before-save flow stays the live executor** (identical, verified numbers),
   and the Context Service + context expression set are the deployed, architecturally-correct
   assets ready to take over.
