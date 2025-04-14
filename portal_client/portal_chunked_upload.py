import hashlib
from io import BytesIO
from os import path
from urllib.parse import urljoin

import backoff
import requests
from tqdm import tqdm


def _generate_md5_hash_for_file_at_path(file_path):
    """
    computes md5 hash for file at given path
    """
    block_size = 65536
    hashing_function = hashlib.md5()
    with open(file_path, "rb") as afile:
        buf = afile.read(block_size)
        while len(buf) > 0:
            hashing_function.update(buf)
            buf = afile.read(block_size)
    return hashing_function.hexdigest()


class ChunkedUploader:
    def __init__(self, base_url, authorization_header):
        self.base_url = base_url
        self.authorization_header = authorization_header

    def upload_chunked_file(self, file_path, early_return_on_error=True, md5=None):
        response = self._chunked_upload_file(
            file_path, early_return_on_error=early_return_on_error, md5=md5
        )
        if response.status_code != requests.codes.ok:
            print(response.text)
            response.raise_for_status()
        return response.json()["file_url"]

    def _chunked_upload_file(
        self,
        file_path,
        early_return_on_error=True,
        md5=None,
        chunk_size_bytes=2 << 20,
    ):
        """
        create generic models with chunkeduploads

        :param chunk_size_bytes: default value is 2 MiB
        """

        chunked_upload_url_suffix = "chunked_uploads/"
        chunked_upload_commit_suffix = "commit/"

        # initial post request to create a new chunked upload instance on the backend side
        file_size = path.getsize(file_path)
        with open(file_path, "rb") as _file:

            def read_chunk():
                return _file.read(chunk_size_bytes)

            # reset the offset
            offset = 0

            # Initialize tqdm progress bar
            with tqdm(
                desc=f"Uploading {path.basename(file_path)}",
                total=file_size,
                unit="iB",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                # First chunk returns some special information
                chunk = BytesIO(read_chunk())
                chunk.name = path.basename(file_path)
                initial_url = urljoin(self.base_url, chunked_upload_url_suffix)
                response = self._upload_first_chunk_of_file(chunk, initial_url)
                bar.update(len(chunk.getvalue()))  # Update progress bar for the first chunk

                if response.status_code is not requests.codes.ok and early_return_on_error:
                    return response

                # fill md5sum and upload_id received from server, required for subsequent requests
                upload_id = response.json()["upload_id"]

                # remember the upload offset
                offset = response.json()["offset"]

                # Continue with other chunks (every other chunk needs to also reference the upload's id
                chunk_count = 0

                add_chunk_url = urljoin(initial_url, "{0}/".format(upload_id))

                for piece in iter(read_chunk, b""):
                    chunk_count += 1
                    chunk = BytesIO(piece)
                    chunk.name = path.basename(file_path)

                    if len(piece) == 0:
                        break
                    response = self._upload_chunk(
                        offset, file_size, chunk, len(piece), add_chunk_url
                    )
                    if (
                        response.status_code is not requests.codes.ok
                        and early_return_on_error
                    ):
                        return response
                    # update the offset
                    offset = response.json()["offset"]
                    bar.update(len(piece))

        # final post including the file's md5 hash
        commit_chunked_upload_url = urljoin(add_chunk_url, chunked_upload_commit_suffix)
        # auto-generate the md5 hash (unless an explicit hash has been provided for testing reason)
        if md5 is None:
            md5 = _generate_md5_hash_for_file_at_path(file_path)
        response = self._commit_chunked_upload(md5, commit_chunked_upload_url)

        return response

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def _upload_first_chunk_of_file(self, chunk: BytesIO, url):
        """
        Helper function that takes care of the initial step of the chunked upload process which includes posting the
        first chunk to the given endpoint and retrieving back some reference for the further uploading process

        :param chunk: the chunk of the file to be uploaded
        :param url: the endpoint to which the data should be posted
        :return: outcome of the first chunk uploading process including the upload_id for later referene on further chunks
        """
        return requests.post(
            url,
            files={"chunk": _clone_chunk(chunk)},
            headers={"Authorization": self.authorization_header},
        )

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def _upload_chunk(self, offset, file_size, chunk, chunk_size, url):
        """
        Helper function that takes care of uploading the subsequent chunks in the chunked upload process

        :param offset: the current offset in the chunk uploading process (what's the starting byte of the current chunk?)
        :param file_size: the total file size of the file to be uploaded in chunks
        :param chunk: the chunk of the file to be uploaded
        :param chunk: the chunk's size in bytes
        :param url: the endpoint to which the data should be posted
        :return: outcome of the chunk uploading process
        """
        return requests.put(
            url,
            files={"chunk": _clone_chunk(chunk)},
            headers={
                "Authorization": self.authorization_header,
                "Content-Range": "bytes %(start)s-%(chunk_size)s/%(file_size)s"
                % {
                    "start": offset,
                    "chunk_size": offset + chunk_size - 1,
                    "file_size": file_size,
                },
                "Content-Disposition": 'filename="%(file_name)s"'
                % {"file_name": chunk.name},
            },
        )

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def _commit_chunked_upload(self, md5, url):
        """
        Helper function that takes care of the final step of the chunked uploading process (committing the upload)
        :param url:
        :param md5: the md5 hash of the uploaded file's contents (used for verification on the server side)
        :return:
        """
        return requests.post(
            url,
            files={"md5": ("", md5)},
            headers={"Authorization": self.authorization_header},
        )


def _clone_chunk(chunk: BytesIO) -> BytesIO:
    # we need to copy the chunk as otherwise, if we retry the function because of an error, the bytes would already be read to the end, resulting in an empty file
    chunk_copy = BytesIO(chunk.getbuffer())
    chunk_copy.name = chunk.name
    return chunk_copy
