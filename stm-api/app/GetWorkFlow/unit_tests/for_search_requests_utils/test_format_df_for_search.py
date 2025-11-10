import sys
import os
import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Adjust path to include the module
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "GetWorkFlow"))
)
from search_requests_utils import format_df_for_search


class TestFormatDfForSearch(unittest.TestCase):
    @patch("search_requests_utils.api")
    def test_format_df_for_search_basic(self, mock_api):
        # Setup mock foc_targets
        mock_api.df_foc_targets = pd.DataFrame(
            {
                "source_requestSource": ["foo"],
                "workOrder_product": ["bar"],
                "source_serviceRegion": ["baz"],
                "source_requestType": ["type"],
                "source_goldenCustomer_id": ["nan"],
                "source_focTarget_new": [np.nan],
                "has_sla_new": [np.nan],
            }
        )

        # Define ALL required columns, including 'workOrder_controlDesk' and others from nan_cols
        query_fields = [
            "lastUpdated",
            "source_requestedStartDate",
            "workOrder_followUpDate",
            "source_orderDate",
            "workOrder_product",
            "source_product",
            "source_serviceRegion",
            "source_goldenCustomer_id",
            "source_requestSource",
            "source_requestType",
            "has_sla",
            "accessPolicyTag",
            "workOrder_controlDesk",  # Add this!
            "workOrder_assignee_id",
            "workOrder_group",
            "workOrder_tags",
            "workOrder_status",
            "source_customerSupportModel",
            "source_status",
            "source_goldenCustomer_name",
            "source_customer",
            "source_customerMarketSegment",
            "source_businessUnit",
            "source_preferredLanguage",
        ]

        # DataFrame must have exactly the columns in query_fields, in the same order
        data = {
            col: [
                "2024-01-01T00:00:00Z"
                if "Date" in col or "lastUpdated" in col
                else ["tag"]
                if col == "accessPolicyTag"
                else "foo"
                if col == "source_requestSource"
                else "bar"
                if col == "source_product" or col == "workOrder_product"
                else "baz"
                if col == "source_serviceRegion"
                else "nan"
                if col == "source_goldenCustomer_id"
                else "type"
                if col == "source_requestType"
                else np.nan
                if col == "has_sla"
                else "control_desk"
                if col == "workOrder_controlDesk"
                else "assignee_id"
                if col == "workOrder_assignee_id"
                else "group"
                if col == "workOrder_group"
                else "tags"
                if col == "workOrder_tags"
                else "status"
                if col == "workOrder_status"
                else "customer_support"
                if col == "source_customerSupportModel"
                else "source_status_val"
                if col == "source_status"
                else "golden_customer_name"
                if col == "source_goldenCustomer_name"
                else "customer"
                if col == "source_customer"
                else "market_segment"
                if col == "source_customerMarketSegment"
                else "business_unit"
                if col == "source_businessUnit"
                else "preferred_language"
                if col == "source_preferredLanguage"
                else None
            ]
            for col in query_fields
        }
        df = pd.DataFrame(data, columns=query_fields)

        # Do NOT add or remove columns before calling the function
        result = format_df_for_search(df, query_fields)

        self.assertIn("source_focTarget", result.columns)
        self.assertIn("has_sla", result.columns)
        self.assertTrue(isinstance(result, pd.DataFrame))


if __name__ == "__main__":
    unittest.main()