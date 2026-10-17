# Historical Event Lab

The Event Lab is data-driven. It renders any validated Research Case in stages. The public source checkout does not include private case packs; import a valid pack or provide case data separately in a private/local deployment before using the library.

1. Context: event information up to the anchor date only.
2. Prediction: a semantic question type such as directional, binary, numeric, categorical, ranking or free text, plus only the relevant learner inputs.
3. Reveal: observed indicator data and synchronized small-multiple summaries.
4. Compare: nuanced classifications such as correct first-order effect or wrong magnitude.
5. Explain: consequence graph and evidence links.
6. Quantify: synthetic portfolio calculations clearly labelled as hypothetical.
7. Decide: risk-management actions and free-text reasoning.

Prediction questions may reference reusable analytical support. Formula support exposes the existing trusted Formula Registry and can open the Formula Playground with the current case values. Transmission support explains channels and competing drivers without inventing a deterministic market equation. Statistical-model support is labelled as an estimate. Support marked `available_before_reveal` is validated against actual or post-event fields.

**Reveal is a pedagogical visual step, not a security boundary.** The current API returns the full case to the browser at the start of the Event Lab, including actual observations and expected answers. The learner can inspect those values before submitting a prediction. Case content must not rely on the UI to keep data confidential; split server responses and a protected reveal request remain future work.

The UK LDI acceptance case uses a transmission explanation for fiscal-to-yields, a duration formula for yield-to-price, a leverage/liquidity feedback mechanism for the crisis-magnitude question, and a competing-channel FX explanation for sterling. The JPY and global-bond cases use the same contract for FX intervention, carry unwind, energy inflation, curve shape and nominal-real yield analysis. The third UK question is binary (`yes`, `no`, `uncertain`) rather than a direction selector.

Actual observations are not invented to fill chart gaps. Missing or unavailable data is shown explicitly.
