# Updated one-minute video

Record the current six-tab UI and actual results. Use the validated run only when the shown values match it. Cut provider waits and label the video **Recorded run · waits shortened**. Keep **Simulated checkout** visible. Pairwise testing is not part of this video.

| Time | Screen | Narration |
| --- | --- | --- |
| 0–8s | RecallTrace introduction | AI agents remember past incidents. But when that memory contains bad advice, they can repeat dangerous mistakes. RecallTrace helps teams investigate and correct those memories. |
| 8–18s | Incident, selected tool, simulated fraud | Our simulated checkout incident retrieves an outdated runbook. The agent disables fraud checks, and simulated fraud rises to 7.1 percent. |
| 18–32s | Replay table and highlighted removal | Black Box replays the recorded decision, removing one memory at a time. Repeated trials show that removing this memory changes the selected action—evidence of influence, not proof of causation. |
| 32–43s | Verified evidence and reviewer approval | Newer verified evidence contradicts the old advice. A reviewer approves the correction, and Atlas preserves the version history. |
| 43–53s | Before/after comparison | With fresh retrieval, the same incident now produces a rollback. Simulated fraud falls to 0.4 percent. |
| 53–60s | Actual `$vectorSearch` source in retrieval.py, then RecallTrace | Voyage powers embeddings. Atlas powers retrieval and governed memory. RecallTrace: investigate the memory, approve the fix, verify the next decision. |

Show a readable excerpt of `backend/app/retrieval.py` with `$vectorSearch` and its tenant/status/expiry filters. Do not show `.env`, connection strings, keys, or private account pages. The event requests code and functionality, so retain the code shot in the final edit.

Export a 60-second video with audio, verify playback, and upload it to the competition-supported destination. The existing downloadable video remains available as a fallback, but predates the latest tabbed visual design. This script does not mean a new recording has already been produced.
