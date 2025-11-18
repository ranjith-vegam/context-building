import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pymilvus import (
    MilvusClient,
    DataType,
    AnnSearchRequest,
    WeightedRanker,
    RRFRanker,
)
from pymilvus.exceptions import MilvusException
from log_manager import get_logger
milvus_logger = get_logger("milvus_logger")

class VectorStoreManager:
    def __init__(self, uri: str):
        self.milvus_client = MilvusClient(uri=uri)
        milvus_logger.info(f"Connected to Milvus at {uri}")

    # ---------------- Partition Management ----------------
    def _partition_exists(self, collection_name: str, partition_name: str) -> bool:
        return self.milvus_client.has_partition(
            collection_name=collection_name, partition_name=partition_name
        )

    def create_partition(self, collection_name: str, partition_name: str):
        if not partition_name:
            partition_name = "_default"

        if self._partition_exists(collection_name, partition_name):
            milvus_logger.info(f"Partition '{partition_name}' already exists.")
            return

        milvus_logger.info(f"Creating new partition '{partition_name}'...")
        self.milvus_client.create_partition(collection_name, partition_name)

    # ---------------- Collection Creation & Schema ----------------
    def _create_collection(self, collection_name: str):
        schema = self.milvus_client.create_schema(
            auto_id=False,
            enable_dynamic_field=True
        )

        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=36)
        schema.add_field("file_id", DataType.VARCHAR, max_length=36)
        schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=1024)
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR, dim)
        schema.add_field("metadata", DataType.JSON)

        self.milvus_client.create_collection(collection_name, schema)

        # ---- Correct Indexing ----
        self.milvus_client.create_index(
            collection_name=collection_name,
            field_name="dense_vector",
            index_params={
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128}
            }
        )

        self.milvus_client.create_index(
            collection_name=collection_name,
            field_name="sparse_vector",
            index_params={
                "index_type": "SPARSE_INVERTED_INDEX",
                "metric_type": "IP",
                "params": {"drop_ratio_build": 0.2}
            }
        )

    # ---------------- Data Upsert & Insert ----------------
    def _prepare_bulk_data(self, documents: list[dict[str, Any]]):
        return [
            {
                "id": str(uuid.uuid4()),
                "file_id": doc.get("file_id", ""),
                "dense_vector": doc.get("dense_vector", []),
                "sparse_vector": doc.get("sparse_vector", {}),
                "metadata": doc.get("metadata", {}),
            }
            for doc in documents
        ]


    def _insert_or_upsert(
        self, 
        method: str, 
        collection_name: str, 
        documents: List[Dict[str, Any]], 
        partition_name: str
    ):
        self.create_partition(collection_name, partition_name)
        data = self._prepare_bulk_data(documents)
        milvus_logger.info(f"{method.title()}ing {len(data)} documents into '{collection_name}' (partition '{partition_name}')")

        fn = getattr(self.milvus_client, method)
        return fn(collection_name=collection_name, data=data, partition_name=partition_name)

    def create_or_upsert_collection(
            self, 
            collection_name: str, 
            documents: List[Dict[str, Any]], 
            partition_name: str = "_default"
    ):
        if not self.milvus_client.has_collection(collection_name):
            milvus_logger.info(f"Collection '{collection_name}' not found. Creating new one...")
            self._create_collection(collection_name)
            return self._insert_or_upsert("insert", collection_name, documents, partition_name)
        return self._insert_or_upsert("upsert", collection_name, documents, partition_name)

    # ---------------- Hybrid Search ----------------
    def hybrid_search(
        self,
        collection_name: str,
        dense_vector: Any,
        sparse_vector: Any,
        partition_names: Optional[List[str]] = None,
        filters: Dict[str, Any] = {},
        ranking_strategy: str = "weighted",
        top_K: int = 10,
    ):
        milvus_logger.info(f"[Milvus Search] Searching in collection: {collection_name}")

        try:
            existing_collections = [c.name if hasattr(c, "name") else c for c in self.milvus_client.list_collections()]
            if collection_name not in existing_collections:
                milvus_logger.error(f"Collection '{collection_name}' not found.")
                return []
        except Exception as e:
            milvus_logger.error(f"Failed to verify collection '{collection_name}': {e}")
            return []

        valid_partitions = []
        if partition_names:
            try:
                all_partitions = [p.name if hasattr(p, "name") else p for p in self.milvus_client.list_partitions(collection_name)]
                valid_partitions = [p for p in partition_names if p in all_partitions]
                milvus_logger.info(f"Valid partitions: {valid_partitions or 'None (searching all)'}")
            except Exception as e:
                milvus_logger.error(f"Failed to list partitions: {e}")

        # Load partitions or collection
        try:
            if valid_partitions:
                self.milvus_client.load_partitions(collection_name, valid_partitions)
            else:
                self.milvus_client.load_collection(collection_name)
        except MilvusException as e:
            milvus_logger.error(f"Load error: {e}")
            self.milvus_client.load_collection(collection_name)

        # Build filter expression
        expressions = []
        for key, value in filters.items():
            if not value or value in ["None", ""]:
                continue
            if key == "date_range" and isinstance(value, (list, tuple)) and len(value) == 2:
                start, end = map(lambda x: int(str(x)[:10]), value)  # handle ms timestamps
                expressions.append(f"created_at >= {start} AND created_at <= {end}")
                continue
            if isinstance(value, list):
                formatted = [f'"{v}"' if isinstance(v, str) else str(v) for v in value]
                expressions.append(f"{key} in [{', '.join(formatted)}]")
            else:
                expressions.append(f'{key} == "{value}"' if isinstance(value, str) else f"{key} == {value}")
        filter_expr = " AND ".join(expressions) if expressions else None

        dense_req = AnnSearchRequest(
            data=[dense_vector],
            anns_field="dense_vector",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_K,
            expr=filter_expr,
        )
        sparse_req = AnnSearchRequest(
            data=[sparse_vector],
            anns_field="sparse_vector",
            param={"metric_type": "IP", "params": {}},
            limit=top_K,
            expr=filter_expr,
        )
        
        # Weighted 0.8 for dense and 0.2 for sparse
        ranker = WeightedRanker(0.8, 0.2) if ranking_strategy == "weighted" else RRFRanker()

        try:
            res = self.milvus_client.hybrid_search(
                collection_name=collection_name,
                reqs=[dense_req, sparse_req],
                ranker=ranker,
                limit=top_K,
                partition_names=valid_partitions or None,
                output_fields=["metadata"],
            )[0]
        except MilvusException as e:
            milvus_logger.error(f"Hybrid search failed in partitions {valid_partitions}: {e}")
            self.milvus_client.load_collection(collection_name)
            res = self.milvus_client.hybrid_search(
                collection_name=collection_name,
                reqs=[dense_req, sparse_req],
                ranker=ranker,
                limit=top_K,
                output_fields=["metadata"],
            )[0]

        return [item.get("entity", {}).get("metadata", {}) for item in res]

vector_store_obj = VectorStoreManager(uri="http://192.168.1.49:19470")