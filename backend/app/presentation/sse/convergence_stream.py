import asyncio
import json


async def convergence_event_stream(job_id: str, orchestrator):
    """PRD Section 7's SSE sketch: replays convergence_history from index 0
    on every new connection (Section 15's reconnect guarantee), terminates
    on 'done' or 'error' -- never spins forever on a failed job."""
    last_sent_index = 0
    while True:
        history = orchestrator.convergence_cache.get(job_id, [])
        for point in list(history)[last_sent_index:]:
            yield f"event: progress\ndata: {json.dumps({'gbest': point})}\n\n"
        last_sent_index = len(history)

        status = orchestrator.job_results.get(job_id, {}).get("status")
        if status == "error":
            yield f"event: error\ndata: {json.dumps(orchestrator.job_results[job_id])}\n\n"
            return
        if status == "done":
            yield f"event: complete\ndata: {json.dumps({'status': 'done'})}\n\n"
            return
        await asyncio.sleep(0.1)
