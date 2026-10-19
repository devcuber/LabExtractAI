import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import get_header_user_id
from models.lab_extraction_request import LabExtractionRequest, LabExtractionStatus
from services.lab_service import ExtractionRequestNotFoundError, LabAnalyzerService


def run(coroutine):
    return asyncio.run(coroutine)


def request_with_header(value=None):
    headers = [] if value is None else [(b"cdie_user_id", str(value).encode())]
    return Request({"type": "http", "headers": headers})


def test_header_user_id_is_parsed_as_uuid():
    user_id = uuid4()
    assert get_header_user_id(cdie_user_id=str(user_id)) == user_id


@pytest.mark.parametrize("value", [None, "not-a-uuid"])
def test_header_user_id_rejects_missing_or_invalid_values(value):
    with pytest.raises(HTTPException) as error:
        get_header_user_id(cdie_user_id=value)
    assert error.value.status_code == 400


def test_result_lookup_uses_user_id_and_hides_other_users_records():
    repository = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = LabAnalyzerService(SimpleNamespace(), repository)
    request_id, user_id = uuid4(), uuid4()

    with pytest.raises(ExtractionRequestNotFoundError):
        run(service.get_extraction_result(request_id, user_id))

    repository.get_by_id.assert_awaited_once_with(request_id, user_id)


def test_enqueue_persists_request_owner():
    user_id = uuid4()
    repository = SimpleNamespace(create=AsyncMock())
    service = LabAnalyzerService(SimpleNamespace(), repository)
    content = b"\x89PNG\r\n\x1a\ncontent"

    run(service.enqueue_for_extraction(content, "estudio.png", user_id=user_id))

    assert repository.create.await_args.args[0].user_id == user_id
