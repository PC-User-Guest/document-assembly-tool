import json
import logging
from kafka import KafkaConsumer, KafkaProducer
from src.document_assembler import DocumentAssembler
from src.advanced_features import concurrency

logger = logging.getLogger(__name__)

class DocumentAssemblyConsumer:
    def __init__(self, bootstrap_servers, input_topic, output_topic, dlq_topic, group_id):
        self.consumer = KafkaConsumer(
            input_topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        self.output_topic = output_topic
        self.dlq_topic = dlq_topic

    def start(self):
        logger.info(f"Kafka consumer started on topic {self.consumer.subscription()}")
        for message in self.consumer:
            job = message.value
            try:
                # Basic validation
                required = ['data_source', 'template_path', 'output_path']
                if not all(k in job for k in required):
                    raise ValueError(f"Missing required fields: {required}")

                # Submit to worker pool
                def process_job(j=job):
                    assembler = DocumentAssembler(
                        data_source=j['data_source'],
                        template_path=j['template_path'],
                        output_path=j['output_path'],
                        data_type=j.get('data_type', 'word')
                    )
                    assembler.run()
                    return j

                # For simplicity in this demo, we'll process synchronously in this loop
                # but in production, we'd use concurrency.process_batch_async
                result = process_job()

                # Success - produce to output topic
                self.producer.send(self.output_topic, {
                    "status": "success",
                    "job": result
                })
                logger.info(f"Job processed successfully: {result['output_path']}")

            except Exception as e:
                logger.error(f"Error processing Kafka job: {e}")
                # Failure - produce to DLQ
                self.producer.send(self.dlq_topic, {
                    "status": "error",
                    "error": str(e),
                    "original_message": job
                })

def start_kafka_consumer(bootstrap_servers, input_topic, output_topic, dlq_topic, group_id):
    consumer = DocumentAssemblyConsumer(bootstrap_servers, input_topic, output_topic, dlq_topic, group_id)
    consumer.start()
