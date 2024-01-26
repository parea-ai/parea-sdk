import os
from typing import Any

import json

from attrs import asdict, define, field

from parea.api_client import HTTPClient
from parea.cache.redis import RedisCache
from parea.constants import PAREA_OS_ENV_EXPERIMENT_UUID
from parea.schemas.log import TraceIntegrations
from parea.schemas.models import TraceLog, UpdateLog
from parea.utils.universal_encoder import json_dumps

LOG_ENDPOINT = "/trace_log"
VENDOR_LOG_ENDPOINT = "/trace_log/{vendor}"


@define
class PareaLogger:
    _client: HTTPClient = field(init=False, default=None)
    _redis_cache: RedisCache = field(init=False, default=None)
    _project_uuid: str = field(init=False, default=None)

    def set_client(self, client: HTTPClient) -> None:
        self._client = client

    def set_redis_cache(self, cache: RedisCache) -> None:
        self._redis_cache = cache

    def set_project_uuid(self, project_uuid: str) -> None:
        self._project_uuid = project_uuid

    def _add_project_uuid_to_data(self, data) -> dict:
        data_dict = asdict(data)
        data_dict["project_uuid"] = self._project_uuid
        return data_dict

    def update_log(self, data: UpdateLog) -> None:
        self._client.request(
            "PUT",
            LOG_ENDPOINT,
            data=asdict(data),
        )

    def record_log(self, data: TraceLog) -> None:
        self._client.request(
            "POST",
            LOG_ENDPOINT,
            data=self._add_project_uuid_to_data(data),
        )

    async def arecord_log(self, data: TraceLog) -> None:
        await self._client.request_async(
            "POST",
            LOG_ENDPOINT,
            data=self._add_project_uuid_to_data(data),
        )

    def write_log(self, data: TraceLog) -> None:
        self._redis_cache.log(data)

    def default_log(self, data: TraceLog) -> None:
        if self._redis_cache:
            self.write_log(data)
        if self._client:
            self.record_log(data)

    def record_vendor_log(self, data: dict[str, Any], vendor: TraceIntegrations) -> None:
        data['project_uuid'] = self._project_uuid
        if experiment_uuid := os.getenv(PAREA_OS_ENV_EXPERIMENT_UUID, None):
            data["experiment_uuid"] = experiment_uuid
        self._client.request(
            "POST",
            VENDOR_LOG_ENDPOINT.format(vendor=vendor.value),
            data=json.loads(json_dumps(data)),  # uuid is not serializable
        )

    async def arecord_vendor_log(self, data: dict[str, Any], vendor: TraceIntegrations) -> None:
        data['project_uuid'] = self._project_uuid
        if experiment_uuid := os.getenv(PAREA_OS_ENV_EXPERIMENT_UUID, None):
            data["experiment_uuid"] = experiment_uuid
        await self._client.request_async(
            "POST",
            VENDOR_LOG_ENDPOINT.format(vendor=vendor.value),
            data=json.loads(json_dumps(data)),  # uuid is not serializable
        )


parea_logger = PareaLogger()
