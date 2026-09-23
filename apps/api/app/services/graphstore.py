from __future__ import annotations

import logging
import re
from typing import Any

from app.config import settings
from app.services.entities import extract_graph

logger = logging.getLogger("atrium.graph")


class GraphStore:
    """Neo4j knowledge graph. Disabled when NEO4J_URI is empty or unreachable."""

    def __init__(self) -> None:
        self._driver = None
        if not settings.neo4j_uri:
            return
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            self._driver.verify_connectivity()
        except Exception as exc:
            logger.warning("Neo4j unavailable: %s", exc)
            self._driver = None

    @property
    def enabled(self) -> bool:
        return self._driver is not None

    def health(self) -> dict[str, Any]:
        if not self._driver:
            return {"ok": False, "enabled": False}
        try:
            self._driver.verify_connectivity()
            return {"ok": True, "enabled": True}
        except Exception as exc:  # pragma: no cover
            return {"ok": False, "enabled": True, "error": str(exc)}

    def upsert_document(self, filename: str, pages: int, chunks: list[str]) -> None:
        if not self._driver:
            return
        payload = [{"index": index, "text": chunk[:400]} for index, chunk in enumerate(chunks)]
        with self._driver.session() as session:
            session.execute_write(_write_document, filename, pages, payload)
            for index, chunk in enumerate(chunks):
                extracted = extract_graph(chunk, filename)
                session.execute_write(_write_entities, filename, index, extracted)

    def hybrid_search(self, query: str, vector_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """GraphRAG local search: vector chunks + 1-hop entity neighbors + extra chunks."""
        if not vector_hits:
            return []
        if not self._driver:
            return vector_hits
        enriched: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        with self._driver.session() as session:
            for hit in vector_hits:
                filename = str(hit.get("filename") or "")
                index = int(hit.get("chunk_index") or 0)
                key = (filename, index)
                if key in seen:
                    continue
                seen.add(key)
                extra = session.execute_read(_expand_chunk, filename, index)
                item = dict(hit)
                item["entities"] = extra.get("entities") or []
                item["neighbors"] = extra.get("neighbors") or []
                enriched.append(item)
                for related in extra.get("related_chunks") or []:
                    rel_key = (related["filename"], related["chunk_index"])
                    if rel_key in seen:
                        continue
                    seen.add(rel_key)
                    enriched.append(
                        {
                            "text": related.get("text") or "",
                            "filename": related["filename"],
                            "chunk_index": related["chunk_index"],
                            "distance": float(hit.get("distance") or 0) + 0.05,
                            "via": "graph",
                            "entities": related.get("entities") or [],
                        }
                    )
        return enriched[:12]

    def entity_search(self, query: str) -> dict[str, Any]:
        if not self._driver:
            return {"ok": False, "enabled": False, "entities": [], "relations": []}
        tokens = [
            token.lower()
            for token in re.findall(r"[A-Za-z0-9@._-]{3,}", query or "")
            if token.lower()
            not in {
                "who",
                "the",
                "and",
                "for",
                "connected",
                "related",
                "which",
                "entities",
                "pathfinder",
                "graphrag",
                "with",
                "from",
            }
        ]
        with self._driver.session() as session:
            return session.execute_read(_search_entities, tokens or [query.lower().strip()])

    def rebuild_from_chunks(self, filename: str, pages: int, chunks: list[str]) -> dict[str, int]:
        self.upsert_document(filename, pages, chunks)
        extracted = extract_graph("\n".join(chunks), filename)
        return {"entities": len(extracted["entities"]), "relations": len(extracted["relations"])}

    def knowledge_graph(self) -> dict[str, list]:
        if not self._driver:
            return {"nodes": [], "edges": []}
        with self._driver.session() as session:
            return session.execute_read(_read_knowledge)

    def close(self) -> None:
        if self._driver:
            self._driver.close()


def _write_document(tx, filename: str, pages: int, chunks: list[dict[str, Any]]) -> None:
    tx.run(
        """
        MERGE (d:Document {filename: $filename})
        SET d.pages = $pages
        WITH d
        OPTIONAL MATCH (d)-[:HAS_CHUNK]->(old:Chunk)
        DETACH DELETE old
        """,
        filename=filename,
        pages=pages,
    )
    for chunk in chunks:
        tx.run(
            """
            MATCH (d:Document {filename: $filename})
            CREATE (c:Chunk {index: $index, text: $text, filename: $filename})
            CREATE (d)-[:HAS_CHUNK]->(c)
            """,
            filename=filename,
            index=chunk["index"],
            text=chunk["text"],
        )


def _read_knowledge(tx) -> dict[str, list]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    docs = tx.run("MATCH (d:Document) RETURN d.filename AS filename, d.pages AS pages")
    for record in docs:
        filename = record["filename"]
        nodes.append(
            {
                "id": f"doc:{filename}",
                "label": filename,
                "kind": "document",
                "detail": f"{record['pages'] or 0} pages",
                "layer": 0,
                "row": len([node for node in nodes if node["kind"] == "document"]),
            }
        )
    chunks = tx.run(
        """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
        RETURN d.filename AS filename, c.index AS index
        ORDER BY filename, index
        """
    )
    for record in chunks:
        filename = record["filename"]
        index = record["index"]
        chunk_id = f"chunk:{filename}:{index}"
        nodes.append(
            {
                "id": chunk_id,
                "label": f"chunk {index}",
                "kind": "chunk",
                "detail": filename,
                "layer": 1,
                "row": len([node for node in nodes if node["kind"] == "chunk"]),
            }
        )
        edges.append({"from": f"doc:{filename}", "to": chunk_id, "label": "HAS_CHUNK"})
    ents = tx.run(
        """
        MATCH (e:Entity)
        RETURN e.key AS key, e.name AS name, e.kind AS kind
        LIMIT 40
        """
    )
    for record in ents:
        nodes.append(
            {
                "id": f"ent:{record['key']}",
                "label": record["name"],
                "kind": "entity",
                "detail": record["kind"],
                "layer": 2,
                "row": len([node for node in nodes if node["kind"] == "entity"]),
            }
        )
    mentions = tx.run(
        """
        MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
        RETURN c.filename AS filename, c.index AS index, e.key AS key
        LIMIT 80
        """
    )
    for record in mentions:
        edges.append(
            {
                "from": f"chunk:{record['filename']}:{record['index']}",
                "to": f"ent:{record['key']}",
                "label": "MENTIONS",
            }
        )
    rels = tx.run(
        """
        MATCH (a:Entity)-[r]->(b:Entity)
        RETURN a.key AS src, b.key AS dst, type(r) AS rel
        LIMIT 40
        """
    )
    for record in rels:
        edges.append({"from": f"ent:{record['src']}", "to": f"ent:{record['dst']}", "label": record["rel"]})
    return {"nodes": nodes, "edges": edges}


def _write_entities(tx, filename: str, index: int, extracted: dict[str, Any]) -> None:
    for entity in extracted.get("entities") or []:
        tx.run(
            """
            MERGE (e:Entity {key: $key})
            SET e.name = $name, e.kind = $kind
            WITH e
            MATCH (c:Chunk {filename: $filename, index: $index})
            MERGE (c)-[:MENTIONS]->(e)
            """,
            key=entity["key"],
            name=entity["name"],
            kind=entity["kind"],
            filename=filename,
            index=index,
        )
    for rel in extracted.get("relations") or []:
        tx.run(
            """
            MATCH (a:Entity {key: $src}), (b:Entity {key: $dst})
            MERGE (a)-[r:RELATES {type: $type}]->(b)
            """,
            src=rel["from"],
            dst=rel["to"],
            type=rel.get("type") or "CO_OCCURS",
        )


def _expand_chunk(tx, filename: str, index: int) -> dict[str, Any]:
    ents = [
        record["name"]
        for record in tx.run(
            """
            MATCH (c:Chunk {filename: $filename, index: $index})-[:MENTIONS]->(e:Entity)
            RETURN e.name AS name
            """,
            filename=filename,
            index=index,
        )
    ]
    neighbors = [
        record["name"]
        for record in tx.run(
            """
            MATCH (c:Chunk {filename: $filename, index: $index})-[:MENTIONS]->(e:Entity)
            MATCH (e)-[:RELATES]-(other:Entity)
            RETURN DISTINCT other.name AS name
            LIMIT 12
            """,
            filename=filename,
            index=index,
        )
    ]
    related = []
    for record in tx.run(
        """
        MATCH (c:Chunk {filename: $filename, index: $index})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(other:Chunk)
        WHERE other.filename <> $filename OR other.index <> $index
        RETURN other.filename AS filename, other.index AS index, other.text AS text,
               collect(DISTINCT e.name) AS entities
        LIMIT 6
        """,
        filename=filename,
        index=index,
    ):
        related.append(
            {
                "filename": record["filename"],
                "chunk_index": record["index"],
                "text": record["text"],
                "entities": record["entities"],
            }
        )
    return {"entities": ents, "neighbors": neighbors, "related_chunks": related}


def _search_entities(tx, tokens: list[str]) -> dict[str, Any]:
    needles = [token.strip().lower() for token in tokens if token and token.strip()]
    records = tx.run(
        """
        MATCH (e:Entity)
        WHERE any(needle IN $needles WHERE toLower(e.name) CONTAINS needle OR toLower(e.key) CONTAINS needle)
        OPTIONAL MATCH (e)-[r:RELATES]-(other:Entity)
        OPTIONAL MATCH (c:Chunk)-[:MENTIONS]->(e)
        RETURN e.name AS name, e.kind AS kind, e.key AS key,
               collect(DISTINCT other.name)[0..8] AS neighbors,
               collect(DISTINCT c.filename)[0..8] AS files
        LIMIT 20
        """,
        needles=needles,
    )
    entities = []
    for record in records:
        entities.append(
            {
                "name": record["name"],
                "kind": record["kind"],
                "neighbors": [item for item in (record["neighbors"] or []) if item],
                "files": [item for item in (record["files"] or []) if item],
            }
        )
    return {"ok": True, "enabled": True, "query": " ".join(needles), "entities": entities}


_graph: GraphStore | None = None


def get_graphstore() -> GraphStore:
    global _graph
    if _graph is None or not _graph.enabled:
        _graph = GraphStore()
    return _graph
