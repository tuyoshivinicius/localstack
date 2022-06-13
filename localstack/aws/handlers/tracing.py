import copy
import logging
from typing import Dict, Optional

from botocore.parsers import create_parser as create_response_parser

from localstack.aws.api import RequestContext, ServiceRequest, ServiceResponse
from localstack.aws.chain import HandlerChain
from localstack.http import Response

LOG = logging.getLogger(__name__)


class Trace:
    request_id: str
    request_context: RequestContext
    request_after_parse: Optional[ServiceRequest]
    request_after_dispatch: Optional[ServiceRequest]
    caught_exception: Optional[Exception]
    http_response: Optional[Response]
    parsed_response: Optional[ServiceResponse]

    def __init__(self, request_contex: RequestContext) -> None:
        super().__init__()
        self.request_id = str(hash(request_contex))
        self.request_context = request_contex
        self.request_after_parse = None
        self.request_after_dispatch = None
        self.caught_exception = None
        self.http_response = None
        self.parsed_response = None


class TracingHandler:
    traces: Dict[RequestContext, Trace]

    def __init__(self) -> None:
        self.traces = {}

    def create_trace(self, chain: HandlerChain, context: RequestContext, response: Response):
        trace = Trace(context)
        self.traces[context] = trace

    def _get_trace_for_context(self, context: RequestContext):
        return self.traces[context]

    def record_parsed_request(
        self, chain: HandlerChain, context: RequestContext, response: Response
    ):
        trace = self._get_trace_for_context(context)
        trace.request_after_parse = copy.deepcopy(context.service_request)

    def record_dispatched_request(
        self, chain: HandlerChain, context: RequestContext, response: Response
    ):
        trace = self._get_trace_for_context(context)
        trace.request_after_dispatch = copy.deepcopy(context.service_request)

    def record_exception(
        self, chain: HandlerChain, exception: Exception, context: RequestContext, response: Response
    ):
        trace = self._get_trace_for_context(context)
        trace.caught_exception = exception

    def record_response(self, chain: HandlerChain, context: RequestContext, response: Response):
        trace = self._get_trace_for_context(context)

        # check if response is set
        if not response.response:
            return

        trace.http_response = response
        try:
            trace.parsed_response = self._parse_response(context, response)
        except Exception:
            LOG.exception("Error parsing response")

    def _parse_response(self, context: RequestContext, response: Response) -> ServiceResponse:
        operation_model = context.operation
        response_dict = {  # this is what botocore.endpoint.convert_to_response_dict normally does
            "headers": dict(response.headers.items()),  # boto doesn't like werkzeug headers
            "status_code": response.status_code,
            "body": response.data,
            "context": {
                "operation_name": operation_model.name,
            },
        }

        parser = create_response_parser(context.service.protocol)
        return parser.parse(response_dict, operation_model.output_shape)

    def log_trace(self, chain: HandlerChain, context: RequestContext, response: Response):
        trace = self._get_trace_for_context(context)
        # here you can do anything based on the trace, check the response status code, check whether an exception was
        # raised ...

        LOG.info("=========================================== TRACE")
        LOG.info("%s.%s", context.service.service_name, context.operation.name)
        LOG.info(" - request after parse:    %s", trace.request_after_parse)
        LOG.info(" - request after dispatch: %s", trace.request_after_dispatch)
        LOG.info(" - response status code:   %s", trace.http_response.status_code)
        LOG.info(" - caught exception:       %s", trace.caught_exception)
        LOG.info(" - parsed response:        %s", trace.parsed_response)
