import grpc
from concurrent import futures
import time
import logging

from src.proto import assembler_pb2
from src.proto import assembler_pb2_grpc
from src.document_assembler import DocumentAssembler
from src.advanced_features import metrics

logger = logging.getLogger(__name__)

def run_assembly(r):
    assembler = DocumentAssembler(
        data_source=r.data_source,
        template_path=r.template_path,
        output_path=r.output_path,
        data_type=r.data_type
    )
    try:
        assembler.run()
        return (True, r.output_path, "")
    except Exception as e:
        return (False, r.output_path, str(e))

class DocumentAssemblerServicer(assembler_pb2_grpc.DocumentAssemblerServicer):
    def AssembleDocument(self, request, context):
        success, path, msg = run_assembly(request)
        return assembler_pb2.AssembleResponse(success=success, output_path=path, message=msg)

    def BatchAssemble(self, request, context):
        reqs = list(request.requests)
        if request.use_processes:
            with futures.ProcessPoolExecutor() as executor:
                results = list(executor.map(run_assembly, reqs))
        else:
            with futures.ThreadPoolExecutor() as executor:
                results = list(executor.map(run_assembly, reqs))

        responses = [
            assembler_pb2.AssembleResponse(success=r[0], output_path=r[1], message=r[2])
            for r in results
        ]
        return assembler_pb2.BatchResponse(responses=responses)

    def HealthCheck(self, request, context):
        return assembler_pb2.HealthResponse(status="SERVING")

    def GetMetrics(self, request, context):
        m = metrics.get_all_metrics()
        return assembler_pb2.MetricsResponse(metrics=m)

def serve(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    assembler_pb2_grpc.add_DocumentAssemblerServicer_to_server(DocumentAssemblerServicer(), server)
    server.add_insecure_port(f'[::]:{port}')
    logger.info(f"gRPC server started on port {port}")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()
