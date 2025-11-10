import traceback
import pika, sys, os
import os
import parsing_skill_config
import time
import logging
import pyodbc
from logging.handlers import TimedRotatingFileHandler

from shared.all_envs import RABBIT_USER, RABBIT_PWD, RABBIT_IP, RABBIT_PORT, SQL_SERVER, DATABASE, SQL_USER, SQL_PASS

# Custom TimedRotatingFileHandler to flush after each log entry
class FlushingTimedRotatingFileHandler(TimedRotatingFileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Logger setup
logger = logging.getLogger("Skillset configuration log")
logger.setLevel(logging.INFO)

# File Handler
handler = FlushingTimedRotatingFileHandler('/var/log/skillset_configuration.log',when="midnight",interval=1,backupCount=7)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

username = RABBIT_USER
password = RABBIT_PWD
host_ip = RABBIT_IP
port = RABBIT_PORT

MAX_RETRIES = 3

def create_rmq_channel(rmq_conn_params, queue, sql_db_conn, retry_count_holder):
    # Exception 1 - Artificially raise an exception to simulate the AMQP Connection error scenario (uncomment below line)
    # raise pika.exceptions.AMQPConnectionError()
    connection = pika.BlockingConnection(rmq_conn_params)
    channel = connection.channel()
        
    def callback(ch, method, properties, body):
        try:
            message_body = body.decode()
            logger.debug(" [x] Received %r" % message_body)
            parsing_skill_config.rmp_parsing(message_body, sql_db_conn)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            retry_count_holder['count'] = 0  # Resetting the retry count after successful message processing
        except Exception as e:
            logger.exception(f"Error processing message: {e}")

    # Set up the consumer on the channel
    channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=False)
    return connection, channel


def retry(retry_count_holder):
    retry_count_holder['count'] += 1
    error_message = traceback.format_exc()
    if retry_count_holder['count'] <= MAX_RETRIES:
        logger.warning(f"RMQ - Warning: {error_message}. Retrying attempt {retry_count_holder['count']}/{MAX_RETRIES}")
        time.sleep(10 * retry_count_holder['count'])  # Backoff strategy
        return retry_count_holder
    else:
        logger.exception(f"RMQ - Error: {error_message}. Maximum retries reached.")
        return retry_count_holder


def main():
    credentials = pika.PlainCredentials(username, password)
    rmq_conn_params = pika.ConnectionParameters(host_ip,port,'/',credentials)
    logger.info("[*] Waiting for messages. To exit press CTRL+C")
    retry_count_holder = {'count': 0}
    rmq_conn, channel = None, None
    sql_db_conn = None

    while True:
        try:
            # Check and establish SQL Database connection
            if sql_db_conn is None or sql_db_conn.closed:
                # Exception 2 - Artificially raise an OperationalError to simulate a database connection issue (uncomment below line)
                # raise pyodbc.OperationalError("Simulated database connection error")
                logger.info(f"Opening a new SQL Database connection")
                sql_db_conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS+';TrustServerCertificate=yes')
            
            # Check and establish RabbitMQ connection
            if rmq_conn is None or not rmq_conn.is_open:
                    logger.info(f"Opening a new RabbitMQ connection")
                    rmq_conn, channel = create_rmq_channel(rmq_conn_params, 'Skillsets configuration', sql_db_conn, retry_count_holder)
            if channel is not None:
                # Exception 3 - Artificially raise a message stream lost error on an active channel (uncomment below line) 
                # raise pika.exceptions.StreamLostError("pika.exceptions.StreamLostError: Transport indicated EOF")
                channel.start_consuming()

        except pika.exceptions.ConnectionClosedByBroker as error:
            retry_count_holder = retry(retry_count_holder)
            if retry_count_holder['count'] > MAX_RETRIES:
                break
        
        except pika.exceptions.StreamLostError as error:
            retry_count_holder = retry(retry_count_holder)
            if retry_count_holder['count'] > MAX_RETRIES:
                break

        except pika.exceptions.AMQPError as error:
            retry_count_holder = retry(retry_count_holder)
            if retry_count_holder['count'] > MAX_RETRIES:
                break
            
        except Exception as e:
            logger.exception(f"Catch all exception, if not caught by RMQ exceptions: {e}")
            break

    # Close RabbitMQ connection if open
    if rmq_conn and rmq_conn.is_open:
        try:
            logger.info(f"Closing the RabbitMQ connection")
            rmq_conn.close()
        except pika.exceptions.ConnectionWrongStateError as e:
            logger.exception(f"Error while closing connection: {traceback.format_exc()}")

    # Close SQL Database connection if open
    if sql_db_conn and not sql_db_conn.closed:
        try:
            logger.info(f"Closing the SQL Database connection")
            sql_db_conn.close()
        except Exception as e:
            logger.exception(f"Error while closing SQL Database connection: {e}")


if __name__ == '__main__':
    try:
        main()

    except KeyboardInterrupt:
        logger.info('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

    except Exception as e:
        logger.exception(f"Error occurred: {e}")

    finally:
        logger.info("Flushing all the logger handlers")
        for handler in logger.handlers:
            handler.flush()