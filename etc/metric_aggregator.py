import copy
import datetime
import json
import logging
import os
import sys
from csv import DictReader
from pathlib import Path
from typing import Dict

from localstack.services.plugins import SERVICE_PLUGINS

LOG = logging.getLogger(__name__)


def _init_service_metric_counter() -> Dict:
    metric_recorder = {}
    from localstack.aws.spec import load_service

    for s, provider in SERVICE_PLUGINS.api_provider_specs.items():
        try:
            service = load_service(s)
            ops = {}
            service_attributes = {"pro": "pro" in provider, "community": "default" in provider}
            ops["service_attributes"] = service_attributes
            for op in service.operation_names:
                attributes = {}
                attributes["invoked"] = 0
                if hasattr(service.operation_model(op).input_shape, "members"):
                    params = {}
                    for n in service.operation_model(op).input_shape.members:
                        params[n] = 0
                    attributes["parameters"] = params
                if hasattr(service.operation_model(op), "error_shapes"):
                    exceptions = {}
                    for e in service.operation_model(op).error_shapes:
                        exceptions[e.name] = 0
                    attributes["errors"] = exceptions
                ops[op] = attributes

            metric_recorder[s] = ops
        except Exception:
            LOG.debug(f"cannot load service '{s}'")
    return metric_recorder


def print_usage():
    # TODO
    print("missing argument for directory")


def main():
    if not len(sys.argv) == 2 or not Path(sys.argv[1]).is_dir():
        print_usage()

    metric_recorder_internal = _init_service_metric_counter()
    metric_recorder_external = copy.deepcopy(metric_recorder_internal)
    base_dir = sys.argv[1]
    pathlist = Path(base_dir).rglob("metric-report-raw-data-*.csv")
    for path in pathlist:
        print(f"checking {str(path)}")
        with open(path, "r") as csv_obj:
            csv_dict_reader = DictReader(csv_obj)
            # iterate over each line as an ordered dictionary
            for row in csv_dict_reader:
                if row["xfail"] == "True":
                    print(f"test {row['test_node_id']} marked as xfail")
                    continue
                recorder = (
                    metric_recorder_internal
                    if row["origin"] == "internal"
                    else metric_recorder_external
                )

                service = recorder[row["service"]]
                ops = service[row["operation"]]

                errors = ops.setdefault("errors", {})
                if row["exception"]:
                    exception = row["exception"]
                    if exception not in errors:
                        # TODO check if required
                        # some errors are not explicitly in the shape, but are wrapped in a "CommonServiceException"
                        errors = ops.setdefault("errors_not_in_shape", {})
                    errors[exception] = ops.get(exception, 0) + 1
                elif int(row["response_code"]) >= 300:
                    for expected_error in ops.get("errors", {}).keys():
                        if expected_error in row["response"]:
                            # assume we have a match
                            errors[expected_error] += 1
                            break

                ops["invoked"] += 1
                if not row["parameters"]:
                    params = ops.setdefault("parameters", {})
                    params["_none_"] = params.get("_none_", 0) + 1
                else:
                    for p in row["parameters"].split(","):
                        ops["parameters"][p] += 1

                test_list = ops.setdefault("tests", [])
                if row["test_node_id"] not in test_list:
                    test_list.append(row["test_node_id"])

    dtime = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%s")

    metrics_path = os.path.join(base_dir, "metrics")
    Path(metrics_path).mkdir(parents=True, exist_ok=True)
    fname = os.path.join(
        metrics_path,
        f"metric-report-{dtime}.json",
    )
    with open(fname, "w") as fd:
        fd.write(json.dumps(metric_recorder_external, indent=2))

    fname = os.path.join(
        metrics_path,
        f"metric-report-internal-calls-{dtime}.json",
    )
    with open(fname, "w") as fd:
        fd.write(json.dumps(metric_recorder_internal, indent=2))


if __name__ == "__main__":
    main()
