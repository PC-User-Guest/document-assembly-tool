import grpc
import sys
import os

# Add src to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.proto import assembler_pb2
from src.proto import assembler_pb2_grpc

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = assembler_pb2_grpc.DocumentAssemblerStub(channel)

        # Assemble one document
        print("--- Single Document Assembly ---")
        request = assembler_pb2.AssembleRequest(
            data_source="tests/fixtures/sample_data.docx",
            template_path="tests/fixtures/sample_template.docx",
            output_path="tests/fixtures/grpc_output.docx",
            data_type="word"
        )
        response = stub.AssembleDocument(request)
        print(f"Success: {response.success}, Message: {response.message}")

        # Batch assembly
        print("\n--- Batch Document Assembly ---")
        batch_request = assembler_pb2.BatchRequest(
            requests=[
                assembler_pb2.AssembleRequest(
                    data_source="tests/fixtures/sample_data.docx",
                    template_path="tests/fixtures/sample_template.docx",
                    output_path="tests/fixtures/grpc_batch_1.docx",
                    data_type="word"
                ),
                assembler_pb2.AssembleRequest(
                    data_source="tests/fixtures/sample_data.csv",
                    template_path="tests/fixtures/sample_template.docx",
                    output_path="tests/fixtures/grpc_batch_2.docx",
                    data_type="csv"
                )
            ],
            use_processes=True
        )
        batch_response = stub.BatchAssemble(batch_request)
        for i, resp in enumerate(batch_response.responses):
            print(f"Job {i+1}: Success: {resp.success}, Path: {resp.output_path}")

        # Health check
        print("\n--- Health Check ---")
        health = stub.HealthCheck(assembler_pb2.HealthRequest())
        print(f"Status: {health.status}")

        # Metrics
        print("\n--- Metrics ---")
        metrics = stub.GetMetrics(assembler_pb2.MetricsRequest())
        print("Current Metrics:")
        for k, v in metrics.metrics.items():
            print(f"  {k}: {v}")

if __name__ == '__main__':
    run()
