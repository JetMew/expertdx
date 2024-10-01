import os
import json
import requests
from abc import ABC
from pydantic import Field
from .. import tool_registry
from ..base import Tool, AgentEnum


class LogAnalyzer(Tool, ABC):
    offline: bool = Field(default=True)
    tool_request_url: str = Field(default='')
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/json'
    }

    def __call__(self, data: dict):
        # cached tool observation for offline evaluation
        if self.offline:
            filepath = os.path.join(self.data_dir, f"{data['task_id']}/{self.name}.txt")
            self.logger.info(f"offline simulation of tool requests. loading from {filepath}")
            with open(filepath) as f:
                return f.read()
        else:
            r = requests.post(url=self.tool_request_url, headers=self.headers, data=json.dumps(data))
            res = r.json()
            return res


@tool_registry.register("spark_driver_log_analyzer")
class SparkDriverLogTool(LogAnalyzer):
    name = "spark_driver_log_analyzer"
    description = (
        "The Application Master is a specific task launched by YARN to manage a single application. "
        "For Spark, the driver program runs the application’s main() function and is the place where the SparkContext is created. "
        "The AM log (i.e., Spark Driver Log) captures all activities and events of the driver, "
        "including task scheduling, resource allocation, and any errors or exceptions that occur during the execution of the application. "
        "It’s crucial for debugging application failures and performance issues."
    )
    belong_to = AgentEnum.spark
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("spark_executor_log_analyzer")
class SparkExecLogTool(LogAnalyzer):
    name = "spark_executor_log_analyzer"
    description = (
        "Each YARN container runs a single Spark executor, which is responsible for running the tasks of a Spark application. "
        "The container log records the activities and events of the executor, "
        "including task execution details, resource usage, and any errors or exceptions that occur during task execution. "
        "It’s an essential resource for understanding the performance and behavior of individual tasks."
    )
    belong_to = AgentEnum.yarn
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("spark_history_server_analyzer")
class SparkHistoryServerTool(LogAnalyzer):
    name = "spark_history_server_analyzer"
    description = (
        "The Spark History Server is a web interface that provides a visual representation of completed Spark applications. "
        "It allows users to review the details of past Spark jobs, stages, and tasks, and to understand their performance characteristics. "
        "It also provides access to event timelines, logs, and other detailed diagnostics. "
        "It’s a valuable tool for post-mortem analysis and for improving the performance of Spark applications."
    )
    belong_to = AgentEnum.spark
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("yarn_resource_dashboard_analyzer")
class YARNResDashTool(LogAnalyzer):
    name = "yarn_resource_dashboard_analyzer"
    description = (
        "This is a monitoring tool that provides a visual interface for tracking and managing resources within a YARN cluster. "
        "It allows users to observe the allocation and usage of resources (like CPU, memory, and disk space) across different nodes and applications. "
        "It’s an essential tool for identifying resource bottlenecks and optimizing resource allocation strategies."
    )
    belong_to = AgentEnum.yarn
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("gc_log_analyzer")
class YARNGCLogTool(LogAnalyzer):
    name = "yarn_garbage_collection_analyzer"
    description = (
        "The GC log records the activities of the Java Virtual Machine’s (JVM) garbage collector, which automatically manages the memory used by YARN applications. "
        "It includes details about when garbage collection occurred, how much memory was reclaimed, and how long the process took."
        " Analyzing the GC log can help identify memory-related issues, such as memory leaks or excessive garbage collection, which can significantly impact application performance."
    )
    belong_to = AgentEnum.yarn
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("hive_metastore_log_analyzer")
class HiveMetaLogTool(LogAnalyzer):
    name = "hive_metastore_log_analyzer"
    description = (
        "The Hive metastore is a service that provides metadata about the tables, databases, columns in a table, and Hive data types running on Hive. "
        "The metastore logs record all the activities and events that occur within the Hive metastore, such as changes in database or table structures, and interactions with the metastore during query execution. "
        "Analyzing these logs can help diagnose issues related to metadata operations and Hive query execution."
    )
    belong_to = AgentEnum.hive
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("hive_server2_log_analyzer")
class HiveServer2LogTool(LogAnalyzer):
    name = "hive_server2_log_analyzer"
    description = (
        "HiveServer2 is a service that enables clients to execute queries against Hive. "
        "The HiveServer2 logs record all the activities and events that occur during query execution, such as query submission, query plan, progress, and any errors or exceptions. "
        "These logs are essential for debugging and optimizing Hive queries."
    )
    belong_to = AgentEnum.hive
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("hdfs_nn_log_analyzer")
class HDFSNameNodeLogTool(LogAnalyzer):
    name = "HDFS_namenode_log_analyzer"
    description = (
        "It keeps the directory tree of all files in the file system, and tracks where across the cluster the file data is kept. "
        "The NameNode logs record all activities and events related to these operations. "
        "Analyzing these logs can help identify issues related to file system management, data block distribution, and access control operations."
    )
    belong_to = AgentEnum.hdfs
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }


@tool_registry.register("hdfs_dn_log_analyzer")
class HDFSDataNodeLogTool(LogAnalyzer):
    name = "HDFS_datanode_log_analyzer"
    description = (
        "They store and retrieve blocks when they are told to (by clients or the NameNode), and they report back to the NameNode periodically with lists of blocks that they are storing. "
        "The DataNode logs record all activities and events that occur within the DataNodes. "
        "Analyzing these logs can help diagnose issues related to data storage, retrieval, and replication."
    )
    belong_to = AgentEnum.hdfs
    parameters = {
        "type": "object",
        "properties": {
            "query_reason": {
                "type": "string",
                "description": "The reason of querying this tool.",
            }
        },
        "required": ["query"],
    }

