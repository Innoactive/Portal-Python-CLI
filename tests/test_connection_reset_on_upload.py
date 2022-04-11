from io import BytesIO
import requests
import requests_mock
from portal_client.portal_chunked_upload import _clone_chunk


def consume_chunk(chunk):
    "Reads a chunk of bytes till the end"
    while chunk.read():
        continue


def test_retry_sending_chunk(requests_mock: requests_mock.Mocker):
    # Given a chunk of byte data
    chunk = BytesIO(b"My first chunk")
    print("Hello world")

    # When sending it to the backend, then trying to send it again afterwards
    requests_mock.post("https://test.org/chunked_upload/", text="Success")
    requests.post("https://test.org/chunked_upload/", files={"chunk": chunk})
    requests.post("https://test.org/chunked_upload/", files={"chunk": chunk})

    # Expect the second request to not contain any data as the data has already been read completely
    assert requests_mock.call_count == 2
    assert b"My first chunk" in requests_mock.request_history[0].body
    assert b"My first chunk" not in requests_mock.request_history[1].body


def test_retry_sending_chunk_by_cloning(requests_mock: requests_mock.Mocker):
    # Given a chunk of byte data
    chunk_data = b"My first chunk"
    print("Hello world")

    # When sending it to the backend, then trying to send it again afterwards
    requests_mock.post("https://test.org/chunked_upload/", text="Success")
    requests.post(
        "https://test.org/chunked_upload/", files={"chunk": BytesIO(chunk_data)}
    )
    requests.post(
        "https://test.org/chunked_upload/", files={"chunk": BytesIO(chunk_data)}
    )

    # Expect the second request to not contain any data as the data has already been read completely
    assert requests_mock.call_count == 2
    assert b"My first chunk" in requests_mock.request_history[0].body
    assert b"My first chunk" in requests_mock.request_history[1].body


def test_retry_sending_chunk_by_cloning_underlying_data(
    requests_mock: requests_mock.Mocker,
):
    # Given a chunk of byte data
    original_chunk = BytesIO(b"My first chunk")
    original_chunk.name = "Test"
    print("Hello world")

    # When sending it to the backend, then trying to send it again afterwards
    requests_mock.post("https://test.org/chunked_upload/", text="Success")
    requests.post(
        "https://test.org/chunked_upload/",
        files={"chunk": _clone_chunk(original_chunk)},
    )
    requests.post(
        "https://test.org/chunked_upload/",
        files={"chunk": _clone_chunk(original_chunk)},
    )

    # Expect the second request to not contain any data as the data has already been read completely
    assert requests_mock.call_count == 2
    assert b"My first chunk" in requests_mock.request_history[0].body
    assert b"My first chunk" in requests_mock.request_history[1].body
