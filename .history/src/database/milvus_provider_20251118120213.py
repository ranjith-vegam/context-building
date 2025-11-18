import uuid
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
            collection_name=collection_name,
            partition_name=partition_name
        )

    def create_partition(self, collection_name: str, partition_name: str):
        if not partition_name:
            partition_name = "_default"

        if self._partition_exists(collection_name, partition_name):
            return

        milvus_logger.info(f"Creating new partition '{partition_name}'...")
        self.milvus_client.create_partition(collection_name, partition_name)

    # ---------------- Collection Creation (Auto-Dim) ----------------
    def _create_collection(self, collection_name: str, sample_doc: dict):
        """
        Creates collection with dynamic dimension detection for dense vectors.
        """
        dense_vec_dim = len(sample_doc["dense_vector"])

        schema = self.milvus_client.create_schema(
            auto_id=False,
            enable_dynamic_field=True
        )

        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=36)
        schema.add_field("file_id", DataType.VARCHAR, max_length=36)

        schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=dense_vec_dim)
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field("metadata", DataType.JSON)

        milvus_logger.info(
            f"Creating new collection '{collection_name}' with dim={dense_vec_dim}"
        )
        self.milvus_client.create_collection(collection_name, schema)

        # ---- Dense Vector Index ----
        self.milvus_client.create_index(
            collection_name=collection_name,
            field_name="dense_vector",
            index_params={
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128}
            }
        )

        # ---- Sparse Vector Index ----
        self.milvus_client.create_index(
            collection_name=collection_name,
            field_name="sparse_vector",
            index_params={
                "index_type": "SPARSE_INVERTED_INDEX",
                "metric_type": "IP",
                "params": {"drop_ratio_build": 0.2}
            }
        )

    # ---------------- Prepare Data ----------------
    def _prepare_bulk_data(self, documents: List[Dict[str, Any]]):
        """
        Takes app-level documents and standardizes the rows for Milvus.
        """
        return [
            {
                "id": str(uuid.uuid4()),
                "file_id": doc.get("file_id"),
                "dense_vector": doc.get("dense_vector"),
                "sparse_vector": doc.get("sparse_vector"),
                "metadata": doc.get("metadata"),
            }
            for doc in documents
        ]

    # ---------------- Insert or Upsert ----------------
    def _insert_or_upsert(
        self, method: str, collection_name: str, documents: List[Dict[str, Any]], partition_name: str
    ):
        self.create_partition(collection_name, partition_name)
        data = self._prepare_bulk_data(documents)

        milvus_logger.info(
            f"{method.upper()} {len(data)} docs → '{collection_name}' (partition '{partition_name}')"
        )

        fn = getattr(self.milvus_client, method)

        return fn(
            collection_name=collection_name,
            data=data,
            partition_name=partition_name
        )

    def create_or_upsert_collection(
        self, collection_name: str, documents: List[Dict[str, Any]], partition_name: str = "_default"
    ):
        """
        - If collection doesn't exist → create + insert
        - If exists → upsert
        """

        if not self.milvus_client.has_collection(collection_name):
            milvus_logger.info(
                f"Collection '{collection_name}' not found. Creating a new one..."
            )
            self._create_collection(collection_name, documents[0])
            return self._insert_or_upsert(
                "insert", collection_name, documents, partition_name
            )

        return self._insert_or_upsert(
            "upsert", collection_name, documents, partition_name
        )

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

        # Validate collection
        try:
            collections = self.milvus_client.list_collections()
            names = [c if isinstance(c, str) else c.name for c in collections]
            if collection_name not in names:
                milvus_logger.error(f"Collection '{collection_name}' not found.")
                return []
        except Exception as e:
            milvus_logger.error(f"Collection check failed: {e}")
            return []

        # Validate partitions
        valid_parts = []
        if partition_names:
            try:
                parts = self.milvus_client.list_partitions(collection_name)
                part_names = [p if isinstance(p, str) else p.name for p in parts]
                valid_parts = [p for p in partition_names if p in part_names]
            except Exception as e:
                milvus_logger.error(f"Partition list failed: {e}")

        # Load partitions or collection
        try:
            if valid_parts:
                self.milvus_client.load_partitions(collection_name, valid_parts)
            else:
                self.milvus_client.load_collection(collection_name)
        except:
            self.milvus_client.load_collection(collection_name)

        # ----- Build filter expression -----
        expr_list = []
        for k, v in filters.items():
            if v is None or v == "":
                continue
            if isinstance(v, list):
                expr_list.append(f'{k} in {v}')
            else:
                expr_list.append(f'{k} == "{v}"')

        filter_expr = " AND ".join(expr_list) if expr_list else None

        # ----- Dense & Sparse ANN Requests -----
        dense_req = AnnSearchRequest(
            data=[dense_vector],
            anns_field="dense_vector",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_K,
            expr=filter_expr
        )

        sparse_req = AnnSearchRequest(
            data=[sparse_vector],
            anns_field="sparse_vector",
            param={"metric_type": "IP", "params": {}},
            limit=top_K,
            expr=filter_expr
        )

        # ----- Ranking -----
        if ranking_strategy == "weighted":
            ranker = WeightedRanker(0.8, 0.2)
        else:
            ranker = RRFRanker()

        try:
            results = self.milvus_client.hybrid_search(
                collection_name=collection_name,
                reqs=[dense_req, sparse_req],
                ranker=ranker,
                limit=top_K,
                partition_names=valid_parts or None,
                output_fields=["metadata"],
            )[0]
        except:
            self.milvus_client.load_collection(collection_name)
            results = self.milvus_client.hybrid_search(
                collection_name=collection_name,
                reqs=[dense_req, sparse_req],
                ranker=ranker,
                limit=top_K,
                output_fields=["metadata"],
            )[0]

        return [item.get("entity", {}).get("metadata") for item in results]


# Singleton Instance
vector_store_obj = VectorStoreManager(uri="http://192.168.1.49:19470")