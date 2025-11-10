import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(
                                    os.path.dirname(__file__)
                                    )
                                ))

import pyodbc
import unittest
from GetWorkFlow.search_requests import (
    agent_permissions
)

from GetWorkFlow.search_requests_utils import *
from Elastic.elastic_settings import query_fields
from GetWorkFlow.db import DB

from dotenv import load_dotenv

load_dotenv()
SQL_SERVER = os.getenv('SQL_SERVER')
DATABASE = os.getenv('DATABASE')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')

INDEX_NAME = 'bbm_aiml_stm_unit_tests'


class TestRequestFromElastic(unittest.TestCase):
    """Tests for the get_request_from_elastic() function currently
    implemented in GetWorkFlow/search_request_utils.py"""

    def setUp(self):
        self.elastic_resp_cleaned = get_request_from_elastic(INDEX_NAME, "2020-04-27T10:20:55", size=50_000)

    def test_elastic_resp_size(self):
        print(len(self.elastic_resp_cleaned))
        self.assertGreater(len(self.elastic_resp_cleaned), 10000)

    def test_elastic_resp_request_id(self):   
        self.assertTrue(
            all([(len(d['request_id']) > 1)  for d in self.elastic_resp_cleaned])
        )


class TestElasticResponseToDf(unittest.TestCase):
    """Tests for the elastic_response_to_df() function currently
    implemented in GetWorkFlow/search_request_utils.py"""

    def setUp(self):
        self.elastic_resp_cleaned = get_request_from_elastic(INDEX_NAME, "2020-04-27T10:20:55", size=50_000)
        self.df_resp = pd.DataFrame(self.elastic_resp_cleaned, columns=query_fields)
        self.df_resp = self.df_resp [(self.df_resp ['source.status'] != 'cancelled') &
                                     (self.df_resp ['source.status'] != 'completed')]

        self.df = elastic_response_to_df(
            self.elastic_resp_cleaned, query_fields
        )

    def test_df_shape(self):
        self.assertEqual(self.df.shape, self.df_resp.shape)

    def test_df_columns(self):
        query_field_names = [f.replace('.', '_') for f in query_fields]
        self.assertTrue(all(self.df.columns.values == query_field_names))

    def test_number_nan_values(self):
        df_tmp = self.df.drop(['workOrder_followUpDate'], axis=1).copy()
        self.assertEqual(df_tmp.isnull().sum().sum(), 0)


class TestFilterStatic(unittest.TestCase):

    def setUp(self):
        self.con = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};SERVER='
                +SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS
            )
        self.df = elastic_response_to_df(
            get_request_from_elastic(INDEX_NAME, "2020-04-27T10:20:55", size=50_000), query_fields
        )
        self.tenant = ''
        self.permissions = agent_permissions(self.con, 'luc_clement')
        self.df_common_filter = filter_static(
                self.con, self.df, self.tenant, self.permissions
            )
        self.df_common_filter = filter_static(self.con, self.df, '', self.permissions)

    def test_access_policy_tag_col(self):
        self.assertEqual(self.df_common_filter.accessPolicyTag.str.contains('DIVISION_').sum(), 0)

    def test_check_status_filter(self):
        """Check if the work status filter is correctly applied."""
        today = pd.Timestamp.today()
        num_filter_cols = self.df_common_filter[
            (self.df_common_filter['workOrder_status'].isin(['new','update_received'])) |
            ( 
                (self.df_common_filter['workOrder_status']=='parked') &
                (self.df_common_filter['workOrder_followUpDate'] <= today)
            )
            ].shape[0]

        self.assertEqual(num_filter_cols, self.df_common_filter.shape[0])
    
    def test_work_order_tags(self):
        """Check if the work status filter is correctly applied."""
        contain_work_tag ='|'.join(['distributionmodefilter'])

        self.assertEqual(
            self.df_common_filter['workOrder_tags'].str.contains(contain_work_tag).sum(),
            self.df_common_filter.shape[0]
        )

class TestSplitSkillDictPerSkill(unittest.TestCase):
    
    def setUp(self):
        self.con = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};SERVER='
                +SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS
            )
        self.skillsets = ['6166e891a6a35b0001dd31f1', '6166e8d7a6a35b0001dd31fa']
        self.split_config = {
                            '6166e891a6a35b0001dd31f1_0': 
                               {'skill_id': '6166e891a6a35b0001dd31f1',
                                'requestSource': ['email', 'smartpath'],
                                'customerSupportModel': ['Non-Standard'],
                                'controlDesk': ['hscOttawa'],
                                'preferredlanguage': ['en']},
                            '6166e891a6a35b0001dd31f1_1': 
                               {'skill_id': '6166e891a6a35b0001dd31f1',
                                'requestSource': ['email', 'smartpath'],
                                'customerSupportModel': ['Standard'],
                                'controlDesk': ['hscOttawa'],
                                'preferredlanguage': ['en']},
                            '6166e8d7a6a35b0001dd31fa_0': 
                               {'skill_id': '6166e8d7a6a35b0001dd31fa',
                                'requestSource': ['email', 'smartpath'],
                                'customerSupportModel': ['Non-Standard'],
                                'controlDesk': ['hscOttawa'],
                                'preferredlanguage': ['fr']},
                            '6166e8d7a6a35b0001dd31fa_1': 
                               {'skill_id': '6166e8d7a6a35b0001dd31fa',
                                'requestSource': ['email', 'smartpath'],
                                'customerSupportModel': ['Standard'],
                                'controlDesk': ['hscOttawa'],
                                'preferredlanguage': ['fr']}
                        }
        self.splited_skill_dicts = split_skill_dict_per_skill(self.split_config, self.skillsets)

    
    def test_num_categories_total(self):
        self.assertEqual(len(self.splited_skill_dicts), len(self.skillsets))
        self.assertEqual(
            sum([len(d.keys()) for d in self.splited_skill_dicts]), len(self.split_config.keys())
        )
    
    def test_skill_name_is_same(self):
        for d in self.splited_skill_dicts:
            d_keys = list(d.keys())
            d_keys = [k[:-2] for k in d_keys]
            self.assertEqual(d_keys[0], d_keys[1])


class TestFindAttrsForCategory(unittest.TestCase):

    def setUp(self):

        self.category = {
            'skill_id': '6166e891a6a35b0001dd31f1',
            'requestSource': ['email', 'smartpath'],
            'customerSupportModel': ['Non-Standard'],
            'controlDesk': ['hscOttawa'],
            'preferredlanguage': ['en']
        }
        self.cat_list = find_attrs_for_category(self.category)

    def test_returned_attrs(self):
        self.assertEqual(len(self.cat_list), len(self.category.keys())-1)
        for cat in self.cat_list:
            self.assertIn(cat, self.category.keys())

    
class TestFindRequestForSkill(unittest.TestCase):
    
    def setUp(self):
        self.con = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};SERVER='
                +SQL_SERVER+';DATABASE='+DATABASE+';UID='+SQL_USER+';PWD='+SQL_PASS
            )
        self.df = elastic_response_to_df(
            get_request_from_elastic(INDEX_NAME, "2020-04-27T10:20:55", size=50_000), query_fields
        )
        self.tenant = ''
        self.permissions = agent_permissions(self.con, 'luc_clement')
        self.df_common_filter = filter_static(
                self.con, self.df, self.tenant, self.permissions
            )
        self.df_common_filter = filter_static(self.con, self.df, '', self.permissions)
        self.skills_dict = {'6166e891a6a35b0001dd31f1_0': 
                                    {   'skill_id': '6166e891a6a35b0001dd31f1',
                                        'requestSource': ['email', 'smartpath'],
                                        'customerSupportModel': ['Non-Standard'],
                                        'controlDesk': ['hscOttawa'],
                                        'preferredlanguage': ['en']},
                            '6166e891a6a35b0001dd31f1_1': 
                                    {   'skill_id': '6166e891a6a35b0001dd31f1',
                                        'requestSource': ['email', 'smartpath'],
                                        'customerSupportModel': ['Standard'],
                                        'controlDesk': ['hscOttawa'],
                                        'preferredlanguage': ['en']}
                        }

        self.df_reqs = find_request_for_skill(self.df_common_filter, self.skill_dict)

    
    def test_filtered_requests(self):

        self.assertEqual(self.df_reqs.shape[1], len(query_fields)+1)
        self.assertTrue(self.df_reqs.shape[0] > 1)
    

if __name__ == '__main__':
    unittest.main()
