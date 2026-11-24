# Scenario examples

## Browser or API

For an agent setting with a published value and an unsaved draft, test both directions of the override. Make a test session from published off and draft on, then from published on and draft off. Verify the live test session uses the draft and read the published value again after each run. Capture the setting, candidate revision, session ID, and the API response fields that prove persistence. A scripted controller and a real browser can prove different things, such as browser microphone and audio playback.

A save test should reload the normal screen from a clean client session and confirm that it displays the persisted value. An authorization test should check the protected action or data directly under the other role. For retries or races, assert the durable final state and count externally observable effects.

## Voice

Pick the routes the change affects. For browser audio, use the existing harness or a browser with a synthetic microphone feed and check what comes out at the far end.

In the Skysay case study, the workspace test and public browser link went through their own WebRTC entrypoints. Inbound and outbound used a local SIP loopback with the production build of the worker running locally. The scripted caller used controlled audio and recorded the other end. Provider-backed calls exercised real speech recognition, model inference and synthesis on that isolated stack. This setup exercises SIP signaling and routing locally. Label a carrier or public telephone route as tested only with separate evidence from that route.

For the optional phrase spoken during a knowledge search, the normal scenario needs a plain question, a lookup with a known answer, and caller-side evidence of exactly one phrase before the grounded response. Include an off case. For failure isolation, refuse only the optional synthesis request, record that no phrase clip was prepared, and verify that the same call answers the lookup, ends normally and settles. Use a call ID to correlate evidence. Assert audio from the caller's recording when the claim is about what the caller heard. Measure question end to the first phrase and first substantive word separately, from a shared clock.

A report row can read: “Browser test with phrase synthesis refused. Same call returned the correct answer, hung up normally and settled. Optional phrase count zero. The evidence was a synthetic recording and a correlated transport-failure event.”
