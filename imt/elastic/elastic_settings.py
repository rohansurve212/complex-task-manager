# List of all columns to be extracted from the data
all_cols = ['request_id', 'lastUpdated', 'accessPolicyTag', 'OrderResponse', 'workOrder', 'source', 
            'OrderRelatedParty', 'SearchDetails', 'SearchFilter', 'AttributeFilter', 'AlwaysRejectFilter', 
            'FilterOperator', 'FilterGroup', 'FilterGroupOperator', 'FilterGroupModifier']

# Subset of columns that contain nested data structures
nested_cols = ['OrderResponse', 'source', 'OrderRelatedParty', 'SearchDetails', 'SearchFilter', 'AttributeFilter', 
               'AlwaysRejectFilter', 'FilterOperator', 'FilterGroup', 'FilterGroupOperator', 'FilterGroupModifier']

# Fields used for querying and fetching specific data
query_fields = ["request_id", "source.externalId", "lastUpdated", "accessPolicyTag", "workOrder.status", "workOrder.followUpDate", "workOrder.controlDesk", 
                "workOrder.group", "workOrder.assignee", "workOrder.tags", "source.orderDate",
                "source.requestedStartDate", "source.requestType", "source.requestSource", "source.customerSupportModel",
                "source.businessUnit", "source.status", "source.product", "source.serviceRegion", "source.goldenCustomer",
                "source.customer", "source.customerMarketSegment", "source.preferredLanguage", "source.focTarget", "source.referredType"]


# Environment variable to determine production or testing environment
from shared.all_envs import SMARTPATH_ENV

# Dynamic index name based on environment
INDEX_NAME = 'bbm_aiml_stm_prod_v0919' if SMARTPATH_ENV.upper() == 'PROD' else 'bbm_aiml_stm_uat_1.2'

# Elasticsearch mappings to define the structure of the index
mappings = {
    "mappings" : {
        "properties" : {
            "lastUpdated": {
              "type": "date",
              "format": "yyyy-MM-dd HH:mm:ss.SSSSSZ||strict_date_optional_time_nanos ||epoch_millis"
            },
            "OrderResponse":{
                "type":"flattened"
            },
            "Order":{
                "type":"flattened"
            },
            "workOrder":{
                "type":"flattened"
            },
            "source": {
                "type":"flattened",
            },
            "OrderRelatedParty": {
                "type":"flattened",
            },
            "SearchDetails": {
                "type":"flattened",
            },
            "SearchFilter": {
                "type":"flattened",
            },
            "AttributeFilter": {
                "type":"flattened",
            },
            "AlwaysRejectFilter": {
                "type":"flattened",
            },
            "FilterOperator": {
                "type":"flattened",
            },
            "FilterGroup": {
                "type":"flattened",
            },
            "FilterGroupOperator": {
                "type":"flattened",
            },
            "FilterGroupModifier": {
                "type":"flattened",
            }
        }
    }
}

# Function to generate the authorization header for API requests
def get_auth_header(auth_token):
    return {
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {auth_token}',
}

# Function to create the request body dynamically based on the given parameters
def make_request_body(date, filter_comp=False):
    
    if filter_comp:
    
      return {
        "@type": "SearchDetails",
        "@baseType": "SearchDetails",
        "@schemaLocation": "",
        "name": "smarttask",
        "filter": [
          {
            "@type": "FilterGroup",
            "@baseType": "FilterGroup",
            "@schemaLocation": "",
            "filter": [
              {
                "@type": "AttributeFilter",
                "@baseType": "AttributeFilter",
                "@schemaLocation": "",
                "field": "source.sourceSystemId",
                "value": [
                  "BSD"
                ],
                "operator": "eq",
                "caseInsensitive": "true"
              },
              {
                "@type": "AttributeFilter",
                "@baseType": "AttributeFilter",
                "@schemaLocation": "",
                "field": "lastUpdated",
                "value": [
                  f"{date}"
                ],
                "operator": "gte",
                "caseInsensitive": "true"
              },
              {
                "@type": "AttributeFilter",
                "@baseType": "AttributeFilter",
                "@schemaLocation": "",
                "field": "workOrder.status",
                "value": [
                    "completed", "cancelled"
                ],
                "operator": "neq",
                "caseInsensitive": "true"
            }
            ],
            "groupOperator": "AND"
          }
        ],
        "sort": [
          {
            "field": "source.orderDate",
            "direction": "DESC"
          }
        ]
      }

    else: 

      return {
        "@type": "SearchDetails",
        "@baseType": "SearchDetails",
        "@schemaLocation": "",
        "name": "smarttask",
        "filter": [
          {
            "@type": "FilterGroup",
            "@baseType": "FilterGroup",
            "@schemaLocation": "",
            "filter": [
              {
                "@type": "AttributeFilter",
                "@baseType": "AttributeFilter",
                "@schemaLocation": "",
                "field": "source.sourceSystemId",
                "value": [
                  "BSD"
                ],
                "operator": "eq",
                "caseInsensitive": "true"
              },
              {
                "@type": "AttributeFilter",
                "@baseType": "AttributeFilter",
                "@schemaLocation": "",
                "field": "lastUpdated",
                "value": [
                  f"{date}"
                ],
                "operator": "gte",
                "caseInsensitive": "true"
              }
            ],
            "groupOperator": "AND"
          }
        ],
        "sort": [
          {
            "field": "source.orderDate",
            "direction": "DESC"
          }
        ]
      }

# Function to create an Elasticsearch query for filtering data
def make_elastic_query(date):
  return {
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "workOrder.tags": "SMARTPATH_DISTRIBUTION_MODE_FILTER"
            }
          },
          {
            "range": {
              "lastUpdated": {
                "gte": f"{date}"
              }
            }
          }
        ]
      }
    },
    "fields": [
      "request_id",
      "source.externalId",
      "lastUpdated",
      "accessPolicyTag",
      "workOrder.status",
      "workOrder.followUpDate",
      "workOrder.controlDesk",
      "workOrder.group ",
      "workOrder.assignee",
      "workOrder.tags",
      "source.orderDate",
      "source.requestedStartDate",
      "source.requestType",
      "source.requestSource",
      "source.customerSupportModel",
      "source.businessUnit",
      "source.status",
      "source.product",
      "source.serviceRegion",
      "source.goldenCustomer",
      "source.customer",
      "source.customerMarketSegment",
      "source.preferredLanguage",
      "source.focTarget",
      "source.referredType"
    ]
  }