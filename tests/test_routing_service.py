import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(
                                    os.path.dirname(__file__)
                                    )
                                ))

import pyodbc
import unittest
from datetime import datetime, timezone

from GetWorkFlow.db import DB
from GetWorkFlow.service import RoutingService
from GetWorkFlow.search_requests_utils import *

from dotenv import load_dotenv

load_dotenv()
SQL_SERVER = os.getenv('SQL_SERVER')
DATABASE = os.getenv('DATABASE')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')

class ElasticRequests:
    def __init__(self, index_name):
        self.index_name = index_name
        self.last_request_date = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        self.elastic_requests = get_request_from_elastic(self.index_name, "2020-01-01T14:21:30", size=1_000_000)

    def update_cache(self):
        elastic_requests_new = get_request_from_elastic(self.index_name, self.last_request_date, size=10000)
        self.elastic_requests = update_response_dict_with_new(
            self.elastic_requests, elastic_requests_new
            )
        self.last_request_date = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

e_requests = ElasticRequests('bbm_aiml_stm_unit_tests')


class TestRoutingService(unittest.TestCase):

    def test_run(self):

        con = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS)
        routing_service = RoutingService(con, 'luc.clement', DB.agent())
        request_id, skill_id, from_absent_agent = routing_service.run(e_requests)

        self.assertEqual(request_id, 'bsd_REQQA-466569')
        self.assertEqual(skill_id, '6166e891a6a35b0001dd31f1')
        self.assertEqual(from_absent_agent, False)


if __name__ == '__main__':
    unittest.main()
