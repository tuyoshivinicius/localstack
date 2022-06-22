import copy
import logging
from typing import Optional

from localstack import config
from localstack.aws.api import RequestContext, ServiceRequest
from localstack.aws.chain import HandlerChain
from localstack.http import Response
from localstack.utils.aws.aws_stack import is_internal_call_context

LOG = logging.getLogger(__name__)


class Metric:
    request_id: str
    request_context: RequestContext
    request_after_parse: Optional[ServiceRequest]
    caught_exception: Optional[Exception]

    def __init__(self, request_contex: RequestContext) -> None:
        super().__init__()
        self.request_id = str(hash(request_contex))
        self.request_context = request_contex
        self.request_after_parse = None
        self.caught_exception = None


class MetricCollector:
    node_id = None
    xfail = False
    data = []

    def __init__(self) -> None:
        self.metrics = {}

    def create_metric(self, chain: HandlerChain, context: RequestContext, response: Response):
        if not config.is_collect_metrics_mode():
            return
        metric = Metric(context)
        self.metrics[context] = metric

    def _get_metric_for_context(self, context: RequestContext) -> Metric:
        return self.metrics[context]

    def record_parsed_request(
        self, chain: HandlerChain, context: RequestContext, response: Response
    ):
        if not config.is_collect_metrics_mode():
            return
        metric = self._get_metric_for_context(context)
        metric.request_after_parse = copy.deepcopy(context.service_request)

    def record_exception(
        self, chain: HandlerChain, exception: Exception, context: RequestContext, response: Response
    ):
        if not config.is_collect_metrics_mode():
            return
        metric = self._get_metric_for_context(context)
        metric.caught_exception = exception

    def update_metric_collection(
        self, chain: HandlerChain, context: RequestContext, response: Response
    ):
        if not config.is_collect_metrics_mode() or not context.service_operation:
            return

        is_internal = is_internal_call_context(context.request.headers)
        metric = self._get_metric_for_context(context)

        # parameters might get changed when dispatched to the service - we use the params stored in request_after_parse
        parameters = ",".join(metric.request_after_parse or "")
        MetricCollector.data.append(
            [
                context.service_operation.service,
                context.service_operation.operation,
                context.request.headers,
                parameters,
                response.status_code,
                response.data.decode("utf-8") if response.status_code >= 300 else "",
                metric.caught_exception.__class__.__name__ if metric.caught_exception else "",
                MetricCollector.node_id,
                MetricCollector.xfail,
                "internal" if is_internal else "external",
            ]
        )

        # cleanup
        del self.metrics[context]
