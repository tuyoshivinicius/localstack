import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytest
from _pytest.main import Session
from _pytest.nodes import Item

from localstack.aws.handlers.metric_collector import MetricCollector

BASE_PATH = os.path.join(os.path.dirname(__file__), "../../../target/metric_reports")
FNAME_RAW_DATA_CSV = os.path.join(
    BASE_PATH,
    f"metric-report-raw-data-{datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%s')}.csv",
)

RAW_DATA_HEADER = [
    "service",
    "operation",
    "request_headers",
    "parameters",
    "response_code",
    "response",
    "exception",
    "test_node_id",
    "xfail",
    "origin",
]


@pytest.hookimpl()
def pytest_sessionstart(session: "Session") -> None:
    Path(BASE_PATH).mkdir(parents=True, exist_ok=True)

    with open(FNAME_RAW_DATA_CSV, "w") as fd:
        writer = csv.writer(fd)
        writer.writerow(RAW_DATA_HEADER)


@pytest.hookimpl()
def pytest_runtest_teardown(item: "Item", nextitem: Optional["Item"]) -> None:
    with open(FNAME_RAW_DATA_CSV, "a") as fd:
        writer = csv.writer(fd)
        writer.writerows(MetricCollector.data)
        MetricCollector.data.clear()


@pytest.hookimpl()
def pytest_runtest_call(item: "Item") -> None:
    MetricCollector.node_id = item.nodeid
    MetricCollector.xfail = False
    for _ in item.iter_markers(name="xfail"):
        MetricCollector.xfail = True
    # TODO only works if tests run sequentially
