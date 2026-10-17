import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from models.lab_extraction_request import LabExtractionRequest, LabExtractionStatus
from workers.lab_extraction_worker import LabExtractionWorker


def run(coroutine):
    return asyncio.run(coroutine)


def make_request(status=LabExtractionStatus.PENDING):
    return LabExtractionRequest(
        id=uuid4(),
        file_content=b"content",
        mime_type="image/png",
        original_filename="estudio.png",
        status=status,
        result_json=None,
        error_message=None,
        created_at=datetime.now(timezone.utc),
        completed_at=None,
    )


def test_worker_completes_claimed_request():
    request = make_request()
    repository = SimpleNamespace(
        claim_pending=AsyncMock(return_value=request),
        update=AsyncMock(),
    )
    service = SimpleNamespace(extract_data=AsyncMock(return_value={"resourceType": "Observation"}))
    worker = LabExtractionWorker(asyncio.Queue(), repository, service)

    run(worker.process(request.id))

    repository.claim_pending.assert_awaited_once_with(request.id)
    update = repository.update.await_args
    assert update.args[0] == request.id
    assert update.args[1].status == LabExtractionStatus.COMPLETED
    assert update.args[1].result_json == {"resourceType": "Observation"}
    assert update.args[1].completed_at is not None


def test_worker_marks_failed_when_extraction_raises():
    request = make_request()
    repository = SimpleNamespace(
        claim_pending=AsyncMock(return_value=request),
        update=AsyncMock(),
    )
    service = SimpleNamespace(extract_data=AsyncMock(side_effect=RuntimeError("LLM unavailable")))
    worker = LabExtractionWorker(asyncio.Queue(), repository, service)

    run(worker.process(request.id))

    update = repository.update.await_args
    assert update.args[1].status == LabExtractionStatus.FAILED
    assert update.args[1].error_message == "LLM unavailable"
    assert update.args[1].completed_at is not None


def test_worker_skips_request_that_is_no_longer_pending():
    request_id = uuid4()
    repository = SimpleNamespace(
        claim_pending=AsyncMock(return_value=None),
        update=AsyncMock(),
    )
    service = SimpleNamespace(extract_data=AsyncMock())
    worker = LabExtractionWorker(asyncio.Queue(), repository, service)

    run(worker.process(request_id))

    service.extract_data.assert_not_awaited()
    repository.update.assert_not_awaited()


def test_run_marks_queue_task_done_after_processing_error():
    request_id = uuid4()
    queue = asyncio.Queue()
    repository = SimpleNamespace(claim_pending=AsyncMock(side_effect=RuntimeError("DB error")))
    worker = LabExtractionWorker(queue, repository, SimpleNamespace())

    async def exercise():
        await queue.put(request_id)
        task = asyncio.create_task(worker.run())
        await asyncio.wait_for(queue.join(), timeout=1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    run(exercise())
    assert queue.empty()
